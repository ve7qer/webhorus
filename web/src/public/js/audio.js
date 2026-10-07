class Horus extends AudioWorkletProcessor {

    constructor(options) {
      // The super constructor call is required.
      super();
      this.nin = options.processorOptions.nin
      this.port.onmessage = (event) => {
          this.nin = event.data
      };
      // preallocated sample buffer, grown if needed. Avoids reallocating and
      // copying the whole buffer on every 128 sample render quantum.
      this.audio_buffer = new Int16Array(65536)
      this.length = 0
    }



    process(inputs, outputs, parameters) {
      const input = inputs[0];
      if (input.length >= 1){
        const samples = input[0]
        if (this.length + samples.length > this.audio_buffer.length) {
          const bigger = new Int16Array(Math.max(this.audio_buffer.length * 2, this.length + samples.length))
          bigger.set(this.audio_buffer.subarray(0, this.length))
          this.audio_buffer = bigger
        }
        for (let i = 0; i < samples.length; i++) {
          this.audio_buffer[this.length + i] = samples[i] * 32767
        }
        this.length += samples.length
      }

      if (this.length > this.nin ){
        const to_modem = this.audio_buffer.slice(0, this.nin)
        this.audio_buffer.copyWithin(0, this.nin, this.length)
        this.length -= this.nin
        this.port.postMessage(to_modem, [to_modem.buffer])
      }
      return true;
    }
  }
  registerProcessor('horus', Horus);
