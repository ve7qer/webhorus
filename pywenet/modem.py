from _drs232_ldpc_cffi import ffi as drs232_ffi
from _drs232_ldpc_cffi.lib import MAX_ITER, CODELENGTH, NUMBERPARITYBITS, NUMBERROWSHCOLS, MAX_ROW_WEIGHT, MAX_COL_WEIGHT, H_rows, H_cols, DRS232_PACKET_LEN, drs232_framer_init, drs232_framer_process
from _fsk_cffi import ffi
from _fsk_cffi.lib import fsk_create, fsk_demod_sd, fsk_nin, fsk_get_demod_stats, fsk_demod, fsk_create_hbr, fsk_set_est_limits, fsk_demod_sd_batch
import logging


BYTES_PER_PACKET = 256
CRC_BYTES = 2
PARITY_BYTES = 65

class Modem():
    def __init__(self,
                 samplerate=115177*8,
                 symbolrate=115177,
                 P=None,
                 mode=2,
                 rs232_framing=True
                 ):

        if P == None:
            P = samplerate//symbolrate
        logging.debug(f"Samplerate: {samplerate}")
        logging.debug(f"Symbolrate: {symbolrate}")
        logging.debug(f"P: {P}")
        self.fsk = fsk_create_hbr(
            samplerate,
            symbolrate,
            P,
            mode,
            1200,
            400
        )
        
        self.drs232_ldpc = DRS232_LDPC(rs232_framing=rs232_framing)
        self.sdbuf = ffi.new("float[]", self.nbits)
        self.batch_sdbuf = ffi.new("float[]", self.nbits)
        self.consumed = ffi.new("int *")

    @property
    def nin(self):
        return fsk_nin(self.fsk)

    @property
    def nbits(self):
        return self.fsk.Nbits

    @property
    def stats(self):
        modem_stats = ffi.new("struct MODEM_STATS *")
        fsk_get_demod_stats(self.fsk, modem_stats)
        return modem_stats

    def demodulate(self, samples):
        if len(samples) != self.nin * 2 * 4:
            raise ValueError(
                "Expected data isn't long enough for what the modem is requesting")

        # samples can be bytes, bytearray or a memoryview, no copy is made
        modbuf = ffi.from_buffer("COMP[]", samples)
        fsk_demod_sd(self.fsk, self.sdbuf, modbuf)
        ffi.release(modbuf)

        return self.drs232_ldpc.write(self.sdbuf, self.nbits)

    def demodulate_batch(self, samples):
        """Demodulate as many nin blocks as fit in samples (interleaved float32 I/Q).

        Returns (packets, bytes_consumed). Unused samples should be passed in again
        with the next call.
        """
        nsamples = len(samples) // 8
        # nin varies by up to one symbol either side of N as timing is tracked
        max_bits = (nsamples // max(self.fsk.N - self.fsk.Ts, 1) + 1) * self.nbits
        if max_bits > len(self.batch_sdbuf):
            self.batch_sdbuf = ffi.new("float[]", max_bits)

        modbuf = ffi.from_buffer("COMP[]", samples)
        nbits = fsk_demod_sd_batch(self.fsk, self.batch_sdbuf, len(self.batch_sdbuf), modbuf, nsamples, self.consumed)
        ffi.release(modbuf)

        packets = self.drs232_ldpc.write(self.batch_sdbuf, nbits) if nbits else []
        return packets, self.consumed[0] * 8



class DRS232_LDPC():
    """UW search, de-framing, LDPC decode and CRC check, implemented in C (drs232_framer.c)"""
    def __init__(self, rs232_framing=True):
        ldpc = drs232_ffi.new("struct LDPC *")
        ldpc.max_iter = MAX_ITER
        ldpc.dec_type = 0
        ldpc.q_scale_factor = 1
        ldpc.r_scale_factor = 1
        ldpc.CodeLength = CODELENGTH
        ldpc.NumberParityBits = NUMBERPARITYBITS
        ldpc.NumberRowsHcols = NUMBERROWSHCOLS
        ldpc.max_row_weight = MAX_ROW_WEIGHT
        ldpc.max_col_weight = MAX_COL_WEIGHT
        ldpc.H_rows = H_rows
        ldpc.H_cols = H_cols
        self.rs232_framing = rs232_framing
        if rs232_framing:
            self.bits_per_byte = 10
            logging.debug("RS232 mode")
        else:
            self.bits_per_byte = 8
            logging.debug("Native mode")
        self.symbols_per_packet = (BYTES_PER_PACKET+CRC_BYTES+PARITY_BYTES)*self.bits_per_byte

        self.framer = drs232_ffi.new("struct DRS232_FRAMER *")
        drs232_framer_init(self.framer, ldpc, rs232_framing)
        self.packets_out = None
        self.max_packets = 0

    @property
    def count_packet(self):
        return self.framer.count_packet

    @property
    def count_packet_error(self):
        return self.framer.count_packet_error

    """Processes a buffer of soft decisions"""
    def write(self, sdbuf, n=None):
        if n is None:
            n = len(sdbuf)
        max_packets = n // self.symbols_per_packet + 1
        if max_packets > self.max_packets:
            self.max_packets = max_packets
            self.packets_out = drs232_ffi.new("uint8_t[]", max_packets * DRS232_PACKET_LEN)

        count_before = self.framer.count_packet
        npackets = drs232_framer_process(self.framer, sdbuf, n, self.packets_out, self.max_packets)

        count = self.framer.count_packet
        if count // 40 != count_before // 40:
            logging.info(f"packets: {count} packet_errors:{self.framer.count_packet_error} PER: {self.framer.count_packet_error/count if count > 0 else "."} iter: {self.framer.last_iter}")

        packets = []
        if npackets:
            raw = drs232_ffi.buffer(self.packets_out, npackets * DRS232_PACKET_LEN)
            for i in range(npackets):
                logging.debug("rx packet")
                packets.append(bytes(raw[i*DRS232_PACKET_LEN:(i+1)*DRS232_PACKET_LEN]))
        return packets
