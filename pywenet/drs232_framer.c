#include <string.h>
#include "drs232_framer.h"

/* defined in wenet_scramble.h, which is included by the cffi module source */
extern double scramble_code[];

/* CRC16-CCITT, matches binascii.crc_hqx(data, 0xffff) */
static uint16_t crc16(const uint8_t *data, int len) {
    uint16_t crc = 0xffff;
    for (int i = 0; i < len; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (int j = 0; j < 8; j++) {
            crc = (crc & 0x8000) ? (uint16_t)((crc << 1) ^ 0x1021) : (uint16_t)(crc << 1);
        }
    }
    return crc;
}

void drs232_framer_init(struct DRS232_FRAMER *f, struct LDPC *ldpc, int rs232_framing) {
    memset(f, 0, sizeof(*f));
    f->ldpc = *ldpc;
    f->rs232_framing = rs232_framing;
    if (rs232_framing) {
        f->bits_per_byte = 10;
        /* UW pattern we look for, including start/stop bits */
        f->uw = 0x6AD677BD01ULL; /* 0b0110101011010110011101111011110100000001 */
        f->uw_allowed_errors = 5;
        f->uw_mask = (1ULL << 40) - 1;
    } else {
        f->bits_per_byte = 8;
        f->uw = 0xABCDEF01ULL; /* 0b10101011110011011110111100000001, note this is reversed */
        f->uw_allowed_errors = 4;
        f->uw_mask = (1ULL << 32) - 1;
    }
    f->symbols_per_packet = (DRS232_BYTES_PER_PACKET + DRS232_CRC_BYTES + DRS232_PARITY_BYTES) * f->bits_per_byte;
}

/* decode a fully collected packet, returns 1 if the CRC passed */
static int decode_packet(struct DRS232_FRAMER *f, uint8_t *packet_out) {
    double *sd = f->symbol_buf;

    if (f->rs232_framing) {
        /* remove rs232 start/stop bits and reverse bit order within each byte */
        int k = 0;
        for (int i = 0; i < f->symbols_per_packet; i += f->bits_per_byte) {
            for (int j = 0; j < 8; j++) {
                f->symbol_buf_no_rs232[k + j] = f->symbol_buf[i + 7 - j + 1];
            }
            k += 8;
        }
        sd = f->symbol_buf_no_rs232;
    }

    sd_to_llr(f->llr, sd, f->ldpc.CodeLength);
    f->last_iter = run_ldpc_decoder(&f->ldpc, f->unpacked_packet, f->llr, &f->parity_check_count);

    for (int i = 0; i < DRS232_PACKET_LEN; i++) {
        uint8_t abyte = 0;
        for (int j = 0; j < 8; j++) {
            abyte |= f->unpacked_packet[8 * i + j] << (7 - j);
        }
        packet_out[i] = abyte;
    }

    f->count_packet++;

    uint16_t rx_checksum = crc16(packet_out, DRS232_BYTES_PER_PACKET);
    uint16_t tx_checksum = packet_out[DRS232_BYTES_PER_PACKET] | (packet_out[DRS232_BYTES_PER_PACKET + 1] << 8);
    if (rx_checksum == tx_checksum) {
        return 1;
    }
    f->count_packet_error++;
    return 0;
}

int drs232_framer_process(struct DRS232_FRAMER *f, float sd[], int n, uint8_t packets_out[], int max_packets) {
    int npackets = 0;
    uint8_t scratch[DRS232_PACKET_LEN];

    for (int i = 0; i < n; i++) {
        float symbol = sd[i];

        if (!f->collecting) {
            uint64_t bit = symbol < 0;
            f->bitbuffer = ((f->bitbuffer << 1) | bit) & f->uw_mask;

            /* check if we match uw */
            if (__builtin_popcountll(f->bitbuffer ^ f->uw) <= f->uw_allowed_errors) {
                f->ind = 0;
                f->collecting = 1;
            }
            continue;
        }

        if (f->rs232_framing) {
            f->symbol_buf[f->ind] = symbol;
        } else {
            f->symbol_buf[f->ind] = symbol * scramble_code[f->ind % 1000];
        }
        f->ind++;

        if (f->ind == f->symbols_per_packet) {
            f->collecting = 0;
            uint8_t *out = npackets < max_packets ? &packets_out[npackets * DRS232_PACKET_LEN] : scratch;
            if (decode_packet(f, out) && npackets < max_packets) {
                npackets++;
            }
        }
    }
    return npackets;
}
