class RtlAudioWorker extends AudioWorkletProcessor {

    constructor(options) {
      // The super constructor call is required.
      super();
      this.expected_buffer_length = 512;
      this.number_of_extra_before_start = 80
      this.number_of_extra_before_pause = 50

      // ring buffer of samples waiting to be played, grown if needed
      this.audio_buffer = new Float32Array(1 << 16)
      this.read_index = 0
      this.length = 0

      this.port.onmessage = (event) => {
        this.push(event.data)
        if (this.length > this.expected_buffer_length * this.number_of_extra_before_start) {
            this.port.postMessage(true);
        }
      };
      this.ready = false

      console.log("audio buffer ready")
    }

    push(samples) {
      if (!(samples instanceof Float32Array)) {
        samples = Float32Array.from(samples)
      }
      const capacity = this.audio_buffer.length
      if (this.length + samples.length > capacity) {
        const bigger = new Float32Array(Math.max(capacity * 2, this.length + samples.length))
        this.copy_out(bigger)
        this.audio_buffer = bigger
        this.read_index = 0
      }
      const buffer = this.audio_buffer
      let write_index = (this.read_index + this.length) % buffer.length
      const first = Math.min(samples.length, buffer.length - write_index)
      buffer.set(samples.subarray(0, first), write_index)
      buffer.set(samples.subarray(first), 0)
      this.length += samples.length
    }

    // copy the oldest out.length samples (or everything buffered) to out without consuming them
    copy_out(out) {
      const buffer = this.audio_buffer
      const n = Math.min(out.length, this.length)
      const first = Math.min(n, buffer.length - this.read_index)
      out.set(buffer.subarray(this.read_index, this.read_index + first), 0)
      out.set(buffer.subarray(0, n - first), first)
    }

    shift_to(out) {
      this.copy_out(out)
      this.read_index = (this.read_index + out.length) % this.audio_buffer.length
      this.length -= out.length
    }

    process(inputs, outputs, parameters) {
        const output = outputs[0]
        this.expected_buffer_length =  output[0].length
        if (this.length > output[0].length && this.ready == true){
            if (this.length < output[0].length * this.number_of_extra_before_pause) {
                this.port.postMessage(false);
            }
            this.shift_to(output[0])

        } else if (this.length > output[0].length * this.number_of_extra_before_start) {
            this.shift_to(output[0])


            if (this.ready == false){
                console.log("audio buffer ready to rumble")
                this.ready = true
            }

        } else if (this.ready == true) {
            console.log("rtlsdr -> audio underrun")
            this.ready = false
            this.port.postMessage(false);
        }

        return true;
    }
  }
  registerProcessor('rtlnode', RtlAudioWorker);
