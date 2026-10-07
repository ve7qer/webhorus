from cffi import FFI
import re

ffibuilder = FFI()


def preprocess_h():
    data = """

typedef struct {
  float real;
  float imag;
} COMP;




/*
 ATTENTION!
 If you would like a :
 -- a utility that will handle the caching of fft objects
 -- real-only (no imaginary time component ) FFT
 -- a multi-dimensional FFT
 -- a command-line utility to perform ffts
 -- a command-line utility to perform fast-convolution filtering

 Then see kfc.h kiss_fftr.h kiss_fftnd.h fftutil.c kiss_fastfir.c
  in the tools/ directory.
*/






typedef struct {
    float r;
    float i;
}kiss_fft_cpx;

typedef struct kiss_fft_state* kiss_fft_cfg;

/*
 *  kiss_fft_alloc
 *
 *  Initialize a FFT (or IFFT) algorithm's cfg/state buffer.
 *
 *  typical usage:      kiss_fft_cfg mycfg=kiss_fft_alloc(1024,0,NULL,NULL);
 *
 *  The return value from fft_alloc is a cfg buffer used internally
 *  by the fft routine or NULL.
 *
 *  If lenmem is NULL, then kiss_fft_alloc will allocate a cfg buffer using malloc.
 *  The returned value should be free()d when done to avoid memory leaks.
 *
 *  The state can be placed in a user supplied buffer 'mem':
 *  If lenmem is not NULL and mem is not NULL and *lenmem is large enough,
 *      then the function places the cfg in mem and the size used in *lenmem
 *      and returns mem.
 *
 *  If lenmem is not NULL and ( mem is NULL or *lenmem is not large enough),
 *      then the function returns NULL and places the minimum cfg
 *      buffer size in *lenmem.
 * */

kiss_fft_cfg kiss_fft_alloc(int nfft,int inverse_fft,void * mem,size_t * lenmem);

/*
 * kiss_fft(cfg,in_out_buf)
 *
 * Perform an FFT on a complex input buffer.
 * for a forward FFT,
 * fin should be  f[0] , f[1] , ... ,f[nfft-1]
 * fout will be   F[0] , F[1] , ... ,F[nfft-1]
 * Note that each element is complex and can be accessed like
    f[k].r and f[k].i
 * */
void kiss_fft(kiss_fft_cfg cfg,const kiss_fft_cpx *fin,kiss_fft_cpx *fout);

/*
 A more generic version of the above function. It reads its input from every Nth sample.
 * */
void kiss_fft_stride(kiss_fft_cfg cfg,const kiss_fft_cpx *fin,kiss_fft_cpx *fout,int fin_stride);

/* If kiss_fft_alloc allocated a buffer, it is one contiguous
   buffer and can be simply free()d when no longer needed*/

/*
 Cleans up some memory that gets managed internally. Not necessary to call, but it might clean up
 your compiler output to call this before you exit.
*/
void kiss_fft_cleanup(void);


/*
 * Returns the smallest integer k, such that k>=n and k has only "fast" factors (2,3,5)
 */
int kiss_fft_next_fast_size(int n);

/* for real ffts, we need an even size */




/*---------------------------------------------------------------------------*\

  FILE........: fsk.h
  AUTHOR......: Brady O'Brien
  DATE CREATED: 6 January 2016

  C Implementation of 2FSK/4FSK modulator/demodulator, based on octave/fsk_horus.m

\*---------------------------------------------------------------------------*/

/*
  Copyright (C) 2016 David Rowe

  All rights reserved.

  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU Lesser General Public License version 2.1, as
  published by the Free Software Foundation.  This program is
  distributed in the hope that it will be useful, but WITHOUT ANY
  WARRANTY; without even the implied warranty of MERCHANTABILITY or
  FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public
  License for more details.

  You should have received a copy of the GNU Lesser General Public License
  along with this program; if not, see <http://www.gnu.org/licenses/>.
*/



#define MODE_2FSK 2
#define MODE_4FSK 4

#define MODE_M_MAX 4

#define FSK_SCALE 16383

struct FSK {
    /*  Static parameters set up by fsk_init */
    int Ndft;               /* buffer size for freq offset est fft */
    int Fs;                 /* sample freq */
    int N;                  /* processing buffer size */
    int Rs;                 /* symbol rate */
    int Ts;                 /* samples per symbol */
    int Nmem;               /* size of extra mem for timing adj */
    int P;                  /* oversample rate for timing est/adj */
    int Nsym;               /* Number of symbols spat out in a processing frame */
    int Nbits;              /* Number of bits spat out in a processing frame */
    int f1_tx;              /* f1 for modulator */
    int fs_tx;              /* Space between TX freqs for modulatosr */
    int mode;               /* 2FSK or 4FSK */
    int est_min;            /* Minimum frequency for freq. estimator */
    int est_max;            /* Maximum frequency for freq. estimaotr */
    int est_space;          /* Minimum frequency spacing for freq. estimator */
    float* hann_table;		/* Precomputed or runtime computed hann window table */
    
    /*  Parameters used by demod */
    COMP phi_c[MODE_M_MAX];
    
    kiss_fft_cfg fft_cfg;   /* Config for KISS FFT, used in freq est */
    float norm_rx_timing;   /* Normalized RX timing */
    
    COMP* samp_old;         /* Tail end of last batch of samples */
    int nstash;             /* How many elements are in there */
    
    float* fft_est;			/* Freq est FFT magnitude */
    
    /* Memory used by demod but not important between demod frames */
    
    /*  Parameters used by mod */
    COMP tx_phase_c;        /* TX phase, but complex */ 
    
    /*  Statistics generated by demod */
    float EbNodB;           /* Estimated EbNo in dB */
    float f_est[MODE_M_MAX];/* Estimated frequencies */
    float ppm;              /* Estimated PPM clock offset */
    
    /*  Parameters used by mod/demod and driving code */
    int nin;                /* Number of samples to feed the next demod cycle */
    int burst_mode;         /* enables/disables 'burst' mode */
    
    /*  modem statistic struct */
    struct MODEM_STATS *stats;
    int normalise_eye;      /* enables/disables normalisation of eye diagram */
};

/*
 * Create an FSK config/state struct from a set of config parameters
 * 
 * int Fs - Sample frequency
 * int Rs - Symbol rate
 * int tx_f1 - '0' frequency
 * int tx_fs - frequency spacing
 */
struct FSK * fsk_create(int Fs, int Rs, int M, int tx_f1, int tx_fs);

/*
 * Create an FSK config/state struct from a set of config parameters
 * 
 * int Fs - Sample frequency
 * int Rs - Symbol rate
 * int tx_f1 - '0' frequency
 * int tx_fs - frequency spacing
 */
struct FSK * fsk_create_hbr(int Fs, int Rs, int P, int M, int tx_f1, int tx_fs);

/* 
 * Set a new number of symbols per processing frame
 */
void fsk_set_nsym(struct FSK *fsk,int nsym);

/*
 * Set the minimum and maximum frequencies at which the freq. estimator can find tones
 */
void fsk_set_est_limits(struct FSK *fsk,int fmin, int fmax);

/* 
 * Clear the estimator states
 */
void fsk_clear_estimators(struct FSK *fsk);

/*
 * Fills MODEM_STATS struct with demod statistics
 */
void fsk_get_demod_stats(struct FSK *fsk, struct MODEM_STATS *stats);

/*
 * Destroy an FSK state struct and free it's memory
 * 
 * struct FSK *fsk - FSK config/state struct to be destroyed
 */
void fsk_destroy(struct FSK *fsk);

/*
 * Modulates Nsym bits into N samples
 * 
 * struct FSK *fsk - FSK config/state struct, set up by fsk_create
 * float fsk_out[] - Buffer for N samples of modulated FSK
 * uint8_t tx_bits[] - Buffer containing Nbits unpacked bits
 */
void fsk_mod(struct FSK *fsk, float fsk_out[], uint8_t tx_bits[]);

/*
 * Modulates Nsym bits into N samples
 * 
 * struct FSK *fsk - FSK config/state struct, set up by fsk_create
 * float fsk_out[] - Buffer for N samples of "voltage" used to modulate an external VCO
 * uint8_t tx_bits[] - Buffer containing Nbits unpacked bits
 */
void fsk_mod_ext_vco(struct FSK *fsk, float vco_out[], uint8_t tx_bits[]);

/*
 * Modulates Nsym bits into N complex samples
 * 
 * struct FSK *fsk - FSK config/state struct, set up by fsk_create
 * comp fsk_out[] - Buffer for N samples of modulated FSK
 * uint8_t tx_bits[] - Buffer containing Nbits unpacked bits
 */
void fsk_mod_c(struct FSK *fsk, COMP fsk_out[], uint8_t tx_bits[]);


/*
 * Returns the number of samples needed for the next fsk_demod() cycle
 *
 * struct FSK *fsk - FSK config/state struct, set up by fsk_create
 * returns - number of samples to be fed into fsk_demod next cycle 
 */
uint32_t fsk_nin(struct FSK *fsk);


/*
 * Demodulate some number of FSK samples. The number of samples to be 
 *  demodulated can be found by calling fsk_nin().
 * 
 * struct FSK *fsk - FSK config/state struct, set up by fsk_create
 * uint8_t rx_bits[] - Buffer for Nbits unpacked bits to be written
 * float fsk_in[] - nin samples of modualted FSK
 */
void fsk_demod(struct FSK *fsk, uint8_t rx_bits[],COMP fsk_in[]);

/*
 * Demodulate some number of FSK samples. The number of samples to be 
 *  demodulated can be found by calling fsk_nin().
 * 
 * struct FSK *fsk - FSK config/state struct, set up by fsk_create
 * float rx_bits[] - Buffer for Nbits soft decision bits to be written
 * float fsk_in[] - nin samples of modualted FSK
 */
void fsk_demod_sd(struct FSK *fsk, float rx_bits[],COMP fsk_in[]);

/*
 * Run fsk_demod_sd over as many nin sized blocks as are available in fsk_in,
 * so Python only has to make one call per buffer instead of one per block.
 * Returns the number of soft decision bits written, *consumed is set to the
 * number of samples used.
 */
int fsk_demod_sd_batch(struct FSK *fsk, float rx_bits[], int max_bits, COMP fsk_in[], int nsamples, int *consumed);

/* enables/disables normalisation of eye diagram samples */
  
void fsk_stats_normalise_eye(struct FSK *fsk, int normalise_enable);

/* Set the FSK modem into burst demod mode */

void fsk_enable_burst_mode(struct FSK *fsk,int nsyms);


#define MODEM_STATS_NC_MAX      20
#define MODEM_STATS_NR_MAX      8
#define MODEM_STATS_ET_MAX      8
#define MODEM_STATS_EYE_IND_MAX 160     
#define MODEM_STATS_NSPEC       512
#define MODEM_STATS_MAX_F_HZ    4000
#define MODEM_STATS_MAX_F_EST   4


struct MODEM_STATS {
    int    Nc;
    float  snr_est;                          /* estimated SNR of rx signal in dB (3 kHz noise BW)  */
    COMP   rx_symbols[MODEM_STATS_NR_MAX][MODEM_STATS_NC_MAX+1];
                                             /* latest received symbols, for scatter plot          */
    int    nr;                               /* number of rows in rx_symbols                       */
    int    sync;                             /* demod sync state                                   */
    float  foff;                             /* estimated freq offset in Hz                        */
    float  rx_timing;                        /* estimated optimum timing offset in samples         */
    float  clock_offset;                     /* Estimated tx/rx sample clock offset in ppm         */
    float  sync_metric;                      /* number between 0 and 1 indicating quality of sync  */
    
    /* eye diagram traces */
    /* Eye diagram plot -- first dim is trace number, second is the trace idx */
    float  rx_eye[MODEM_STATS_ET_MAX][MODEM_STATS_EYE_IND_MAX];
    int    neyetr;                           /* How many eye traces are plotted */
    int    neyesamp;                         /* How many samples in the eye diagram */

    /* optional for FSK modems - est tone freqs */

    float f_est[MODEM_STATS_MAX_F_EST];
    
    /* Buf for FFT/waterfall */

    float        fft_buf[2*MODEM_STATS_NSPEC];
    kiss_fft_cfg fft_cfg;
};


"""
    # data += open("./wenet/src/kiss_fft.h", "r").read()
    # data += open("./wenet/src/fsk.h", "r").read()
    # data = re.sub(r'#ifdef.+?#endif','',data, flags=re.DOTALL)
    # data = re.sub(r'#ifndef.+\n','',data)
    # data = re.sub(r'#include.+\n','',data)
    # data = re.sub(r'#endif.*\n','',data)


    # # searches for defines using defines and replaces them
    # max_loop = 100
    # while defines := re.findall(r'^#define +(\w+) +(?!(\d+|free)(?: +.*$)?$)(\w+)(?: +.*)?$',data, flags=re.MULTILINE):
    #     current_define_values = re.findall(r'^#define +(\w+) +(\d+)(?: +.*)?$',data, flags=re.MULTILINE)
    #     current_define_values = { x[0]: x[1] for x in current_define_values}
    #     for define in defines:
    #         print(define)
    #         if define[1] in current_define_values:
    #             data = re.sub('^(#define +'+define[0]+' +)(\w+)((?: +.*)?)$','\\1 '+current_define_values[define[1]]+' \\3', data, flags=re.MULTILINE)
    #     if max_loop == 0:
    #         raise ValueError("Could not replace out all #defines with primatives")
    #     max_loop -= 1
        
    # current_define_values = re.findall(r'^#define +(\w+) +(\d+)(?: +.*)?$',data, flags=re.MULTILINE)
    # current_define_values = { x[0]: int(x[1]) for x in current_define_values}
    # # searches for maths
    # for math_define in re.findall(r'^#define +(\w+) +\((.+?)\)(?: +.*)?$',data, flags=re.MULTILINE):
    #     value = eval(math_define[1],current_define_values)
    #     data = re.sub('^(#define +'+math_define[0]+' +)(.+)((?: +.*)?)$','\\1 '+str(value)+' \\3', data, flags=re.MULTILINE)
    # print(data)
    return data

ffibuilder.cdef(preprocess_h()
    
)

# set_source() gives the name of the python extension module to
# produce, and some C source code as a string.  This C code needs
# to make the declarated functions, types and globals available,
# so it is often just the "#include".

from distutils import sysconfig


ffibuilder.set_source("_fsk_cffi",
"""
     #include "modem_stats.h"
     #include "fsk.h"   // the C header of the library

     int fsk_demod_sd_batch(struct FSK *fsk, float rx_bits[], int max_bits, COMP fsk_in[], int nsamples, int *consumed) {
         int used = 0;
         int nbits = 0;
         while (nsamples - used >= fsk_nin(fsk) && nbits + fsk->Nbits <= max_bits) {
             int nin = fsk_nin(fsk);
             fsk_demod_sd(fsk, &rx_bits[nbits], &fsk_in[used]);
             used += nin;
             nbits += fsk->Nbits;
         }
         *consumed = used;
         return nbits;
     }
""",
      sources=[
        "./wenet/src/fsk.c",
        "./wenet/src/kiss_fft.c",
      ],
       include_dirs = [ "./wenet/src"],
     )   # library name, for the linker

if __name__ == "__main__":
    ffibuilder.compile(verbose=True)