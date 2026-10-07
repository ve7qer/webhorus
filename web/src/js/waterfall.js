// Canvas waterfall. Replaces a Plotly heatmap that re-processed the entire
// buffer (and sorted every cell to pick the colour scale) on every update.
//
// Newest row is drawn at the top. Frequencies passed to setFrequencies,
// setMarkers and setShapes all use the same (arbitrary) units.

const TURBO = [
    [0.0, '#30123b'],
    [0.1, '#4145ab'],
    [0.2, '#4673e0'],
    [0.3, '#34a6dd'],
    [0.4, '#1ed5b6'],
    [0.5, '#32f17e'],
    [0.6, '#90f539'],
    [0.7, '#e4e61a'],
    [0.8, '#fcb414'],
    [0.9, '#f4630a'],
    [1.0, '#b21b0a']
];

// same margins the Plotly layout used
const MARGIN = { l: 40, r: 40, t: 20, b: 40 };

// colour scale is set from the 95th percentile of everything on screen
const HIST_MIN_DB = -200;
const HIST_MAX_DB = 50;
const HIST_STEP_DB = 0.1;

function buildLut(stops) {
    const rgb = stops.map(([pos, hex]) => [pos, parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16)]);
    const lut = new Uint32Array(256);
    const little = new Uint8Array(new Uint32Array([1]).buffer)[0] === 1;
    for (let i = 0; i < 256; i++) {
        const t = i / 255;
        let k = 1;
        while (k < rgb.length - 1 && rgb[k][0] < t) k++;
        const [p0, r0, g0, b0] = rgb[k - 1];
        const [p1, r1, g1, b1] = rgb[k];
        const f = (t - p0) / (p1 - p0);
        const r = Math.round(r0 + (r1 - r0) * f);
        const g = Math.round(g0 + (g1 - g0) * f);
        const b = Math.round(b0 + (b1 - b0) * f);
        lut[i] = little ? (255 << 24) | (b << 16) | (g << 8) | r : (r << 24) | (g << 16) | (b << 8) | 255;
    }
    return lut;
}

export class Waterfall {
    constructor(container, rows) {
        this.container = container;
        this.rows = rows;
        this.canvas = document.createElement('canvas');
        this.canvas.style.display = 'block';
        this.canvas.style.width = '100%';
        this.canvas.style.height = '100%';
        container.appendChild(this.canvas);
        this.ctx = this.canvas.getContext('2d');

        // rows x bins image, scaled up onto the visible canvas
        this.image = document.createElement('canvas');
        this.imageCtx = this.image.getContext('2d');

        this.lut = buildLut(TURBO);
        this.histogram = new Uint32Array(Math.ceil((HIST_MAX_DB - HIST_MIN_DB) / HIST_STEP_DB) + 1);
        this.first = 0;
        this.last = 1;
        this.markers = [];
        this.shapes = [];
        this.bins = 0;
        this.clear();

        new ResizeObserver(() => this.draw()).observe(container);
    }

    clear() {
        this.data = null;
        this.bins = 0;
        this.filled = 0;
        this.head = 0; // index of the next row to write
        this.histogram.fill(0);
        this.draw();
    }

    // centre frequencies of the first and last bins
    setFrequencies(first, last) {
        this.first = first;
        this.last = last;
    }

    setMarkers(xs) {
        this.markers = xs;
    }

    // [{x0, x1}] ranges to grey out
    setShapes(shapes) {
        this.shapes = shapes;
    }

    _resize(bins) {
        this.bins = bins;
        this.data = new Float32Array(bins * this.rows).fill(-Infinity);
        this.filled = 0;
        this.head = 0;
        this.histogram.fill(0);
        this.image.width = bins;
        this.image.height = this.rows;
        this.imageData = this.imageCtx.createImageData(bins, this.rows);
        this.pixels = new Uint32Array(this.imageData.data.buffer);
    }

    _histIndex(v) {
        const i = Math.round((v - HIST_MIN_DB) / HIST_STEP_DB);
        return i < 0 ? 0 : i >= this.histogram.length ? this.histogram.length - 1 : i;
    }

    _histUpdate(offset, delta) {
        for (let i = offset; i < offset + this.bins; i++) {
            const v = this.data[i];
            if (Number.isFinite(v)) {
                this.histogram[this._histIndex(v)] += delta;
            }
        }
    }

    _percentile(q) {
        let total = 0;
        for (let i = 0; i < this.histogram.length; i++) total += this.histogram[i];
        if (total == 0) return null;
        const target = Math.floor(q * (total - 1));
        let seen = 0;
        for (let i = 0; i < this.histogram.length; i++) {
            seen += this.histogram[i];
            if (seen > target) return HIST_MIN_DB + i * HIST_STEP_DB;
        }
        return HIST_MAX_DB;
    }

    // row: dB values, one per bin
    push(row) {
        if (row.length != this.bins) {
            this._resize(row.length);
        }
        const offset = this.head * this.bins;
        if (this.filled == this.rows) {
            this._histUpdate(offset, -1); // forget the row being overwritten
        } else {
            this.filled++;
        }
        this.data.set(row, offset);
        this._histUpdate(offset, 1);
        this.head = (this.head + 1) % this.rows;
        this.render();
    }

    render() {
        if (!this.data) return;
        const p95 = this._percentile(0.95);
        if (p95 === null) return;
        const zmin = p95 - 15;
        const zmax = p95 + 2;
        const scale = 255 / (zmax - zmin);

        // newest row at the top
        for (let y = 0; y < this.rows; y++) {
            const r = (this.head - 1 - y + this.rows) % this.rows;
            const src = r * this.bins;
            const dst = y * this.bins;
            for (let x = 0; x < this.bins; x++) {
                const v = this.data[src + x];
                let c = Number.isFinite(v) ? (v - zmin) * scale : 0;
                c = c < 0 ? 0 : c > 255 ? 255 : c;
                this.pixels[dst + x] = this.lut[c | 0];
            }
        }
        this.imageCtx.putImageData(this.imageData, 0, 0);
        this.draw();
    }

    draw() {
        const dpr = window.devicePixelRatio || 1;
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        if (width == 0 || height == 0) return;
        if (this.canvas.width != Math.round(width * dpr) || this.canvas.height != Math.round(height * dpr)) {
            this.canvas.width = Math.round(width * dpr);
            this.canvas.height = Math.round(height * dpr);
        }
        const ctx = this.ctx;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.clearRect(0, 0, width, height);

        const plotW = width - MARGIN.l - MARGIN.r;
        const plotH = height - MARGIN.t - MARGIN.b;
        if (plotW <= 0 || plotH <= 0 || !this.bins) return;

        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(this.image, MARGIN.l, MARGIN.t, plotW, plotH);

        // bins are drawn as cells centred on their frequency
        const binWidth = this.bins > 1 ? (this.last - this.first) / (this.bins - 1) : 1;
        const start = this.first - binWidth / 2;
        const span = binWidth * this.bins;
        const toPx = (f) => MARGIN.l + ((f - start) / span) * plotW;

        ctx.fillStyle = 'rgba(211, 211, 211, 0.5)';
        for (const shape of this.shapes) {
            const x0 = Math.max(MARGIN.l, Math.min(toPx(shape.x0), toPx(shape.x1)));
            const x1 = Math.min(MARGIN.l + plotW, Math.max(toPx(shape.x0), toPx(shape.x1)));
            if (x1 > x0) ctx.fillRect(x0, MARGIN.t, x1 - x0, plotH);
        }

        // frequency estimate markers, arrows pointing down at the top edge
        ctx.fillStyle = 'black';
        ctx.strokeStyle = 'black';
        ctx.lineWidth = 1;
        for (const f of this.markers) {
            const x = toPx(f);
            if (!Number.isFinite(x) || x < MARGIN.l || x > MARGIN.l + plotW) continue;
            ctx.beginPath();
            ctx.moveTo(x, 2);
            ctx.lineTo(x, MARGIN.t - 6);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(x - 4, MARGIN.t - 7);
            ctx.lineTo(x + 4, MARGIN.t - 7);
            ctx.lineTo(x, MARGIN.t);
            ctx.closePath();
            ctx.fill();
        }
    }
}
