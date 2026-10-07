/*
  drs232_framer: unique word search, RS232/scrambler de-framing, LDPC decode
  and CRC check for Wenet packets.

  This is a C port of the per-bit state machine that used to live in
  pywenet/modem.py (DRS232_LDPC.write). Running it in C avoids a Python
  loop iteration per received bit (~115k per second).
*/

#ifndef __DRS232_FRAMER__
#define __DRS232_FRAMER__

#include <stdint.h>
#include "mpdecode_core.h"

#define DRS232_BYTES_PER_PACKET 256
#define DRS232_CRC_BYTES 2
#define DRS232_PARITY_BYTES 65
#define DRS232_PACKET_LEN (DRS232_BYTES_PER_PACKET + DRS232_CRC_BYTES)
#define DRS232_MAX_SYMBOLS ((DRS232_BYTES_PER_PACKET + DRS232_CRC_BYTES + DRS232_PARITY_BYTES) * 10)

struct DRS232_FRAMER {
    struct LDPC ldpc;
    int rs232_framing;
    int bits_per_byte;
    int symbols_per_packet;
    uint64_t uw;
    uint64_t uw_mask;
    int uw_allowed_errors;

    uint64_t bitbuffer;
    int collecting;
    int ind;

    double symbol_buf[DRS232_MAX_SYMBOLS];
    double symbol_buf_no_rs232[DRS232_MAX_SYMBOLS];
    float llr[DRS232_MAX_SYMBOLS];
    uint8_t unpacked_packet[DRS232_MAX_SYMBOLS];
    int parity_check_count;

    int count_packet;
    int count_packet_error;
    int last_iter;
};

/* ldpc is copied, so it only needs to be valid for the duration of the call */
void drs232_framer_init(struct DRS232_FRAMER *f, struct LDPC *ldpc, int rs232_framing);

/*
  Process n soft decision symbols. Packets that pass CRC are written to
  packets_out (DRS232_PACKET_LEN bytes each, CRC included), up to max_packets.
  Returns the number of packets written.
*/
int drs232_framer_process(struct DRS232_FRAMER *f, float sd[], int n, uint8_t packets_out[], int max_packets);

#endif
