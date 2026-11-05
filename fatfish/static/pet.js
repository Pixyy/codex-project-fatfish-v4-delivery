"use strict";
// Both the native window and this renderer use pets/manifest.json unchanged.
class FishSprite {
  constructor(canvas, options = {}) {
    this.options = options;
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.form = "chibi";
    this.action = "idle";
    this.index = 0;
    this.elapsed = 0;
    this.motion = true;
    this.look = null;
    this.old = null;
    this.transition = 0;
    this.last = 0;
    this.lastPaint = 0;
    this.disposed = false;
    this.images = {};
    this.reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    this.ready = this.load();
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(canvas);
    canvas.addEventListener("pointermove", (e) => {
      const r = canvas.getBoundingClientRect();
      this.look = {
        dx: e.clientX - r.left - r.width / 2,
        dy: e.clientY - r.top - r.height / 2,
        until: performance.now() + 1000,
      };
    });
    document.addEventListener("visibilitychange", () => {
      this.last = 0;
    });
  }
  async load() {
    if (this.options.manifest) this.spec = this.options.manifest;
    else {
      const r = await fetch("/pets/manifest.json");
      if (!r.ok) throw Error("动作配置加载失败");
      this.spec = await r.json();
    }
    await Promise.all(
      Object.entries(this.spec.forms).map(async ([key, form]) => {
        const img = new Image();
        img.src = this.options.assetBase
          ? this.options.assetBase + form.atlas.replace(/^\//, "")
          : form.atlas;
        await img.decode();
        this.images[key] = img;
      }),
    );
    this.resize();
    this.emit();
    requestAnimationFrame((t) => this.tick(t));
    return this;
  }
  resize() {
    const r = this.canvas.getBoundingClientRect();
    this.w = r.width || 360;
    this.h = r.height || 420;
    this.dpr = Math.min(devicePixelRatio || 1, 2);
    this.canvas.width = Math.round(this.w * this.dpr);
    this.canvas.height = Math.round(this.h * this.dpr);
    if (this.spec) this.draw(performance.now());
  }
  setForm(form) {
    if (!this.spec?.forms[form] || this.form === form) return;
    const old = document.createElement("canvas");
    old.width = this.canvas.width;
    old.height = this.canvas.height;
    old.getContext("2d").drawImage(this.canvas, 0, 0);
    this.old = old;
    this.transition = performance.now() + 400;
    this.form = form;
    this.index = 0;
    this.elapsed = 0;
    this.draw(performance.now());
    this.emit();
  }
  play(action) {
    if (!this.spec?.forms[this.form].animations[action]) return;
    this.action = action;
    this.index = 0;
    this.elapsed = 0;
    this.look = null;
    this.emit();
    this.draw(performance.now());
  }
  setMotion(value) {
    this.motion = !!value;
    this.last = 0;
    this.draw(performance.now());
    this.emit();
  }
  emit() {
    this.canvas.dataset.form = this.form;
    this.canvas.dataset.action = this.action;
    this.canvas.dispatchEvent(
      new CustomEvent("petstate", {
        detail: { form: this.form, action: this.action, motion: this.motion },
      }),
    );
  }
  tick(now) {
    if (this.disposed) return;
    requestAnimationFrame((t) => this.tick(t));
    if (document.hidden) {
      this.last = now;
      return;
    }
    const dt = this.last ? Math.min(100, now - this.last) : 0;
    this.last = now;
    if (this.motion && !this.reduce) {
      this.elapsed += dt;
      let clip = this.spec.forms[this.form].animations[this.action];
      while (this.elapsed >= clip.durations[this.index]) {
        this.elapsed -= clip.durations[this.index];
        this.index++;
        if (this.index >= clip.frames.length) {
          if (clip.loop) this.index = 0;
          else {
            this.action = "idle";
            this.index = 0;
            this.elapsed = 0;
            this.emit();
          }
          clip = this.spec.forms[this.form].animations[this.action];
        }
      }
    }
    if (now - this.lastPaint > 32) {
      this.draw(now);
      this.lastPaint = now;
    }
  }
  frame(now) {
    const spec = this.spec.forms[this.form],
      clip = spec.animations[this.action];
    let frame = clip.frames[this.index];
    if (
      this.motion &&
      !this.reduce &&
      this.action === "idle" &&
      this.look?.until > now &&
      spec.lookDirections?.length &&
      Math.abs(this.look.dx) + Math.abs(this.look.dy) > 45
    ) {
      const degrees =
        ((Math.atan2(this.look.dx, -this.look.dy) * 180) / Math.PI + 360) % 360;
      let best = spec.lookDirections[0],
        distance = Infinity;
      for (const d of spec.lookDirections) {
        const delta = Math.abs(((d.degrees - degrees + 540) % 360) - 180);
        if (delta < distance) {
          best = d;
          distance = delta;
        }
      }
      frame = [best.column, best.row];
    }
    return frame;
  }
  draw(now) {
    if (!this.spec || !this.images[this.form]) return;
    const ctx = this.ctx;
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.clearRect(0, 0, this.w, this.h);
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    const spec = this.spec.forms[this.form],
      img = this.images[this.form],
      cw = img.width / spec.columns,
      ch = img.height / spec.rows,
      crop = spec.crop || [0, 0, cw, ch];
    const f = this.frame(now);
    let h = Math.min(this.h - 25, spec.height),
      w = (h * crop[2]) / crop[3],
      y = this.h - 16 - h;
    if (w > this.w - 16) {
      h *= (this.w - 16) / w;
      w = this.w - 16;
      y = this.h - 16 - h;
    }
    if (this.motion && !this.reduce && this.form === "mature")
      y += Math.sin(now / 650) * 1.7;
    if (
      this.motion &&
      !this.reduce &&
      this.form === "mature" &&
      this.action === "jump"
    )
      y -= Math.abs(Math.sin((this.elapsed / 900) * Math.PI)) * 25;
    let alpha = 1;
    if (this.old && now < this.transition) {
      alpha = 1 - (this.transition - now) / 400;
      ctx.globalAlpha = 1 - alpha;
      ctx.drawImage(this.old, 0, 0, this.w, this.h);
    } else this.old = null;
    ctx.globalAlpha = alpha;
    ctx.drawImage(
      img,
      f[0] * cw + crop[0],
      f[1] * ch + crop[1],
      crop[2],
      crop[3],
      (this.w - w) / 2,
      y,
      w,
      h,
    );
    ctx.globalAlpha = 1;
    if (alpha < 1) {
      ctx.fillStyle = "#9cb9e8";
      for (let i = 0; i < 9; i++) {
        const a = (i * Math.PI * 2) / 9 + now / 500;
        ctx.beginPath();
        ctx.arc(
          this.w / 2 + Math.cos(a) * w * 0.6,
          this.h / 2 + Math.sin(a) * h * 0.45,
          2.2,
          0,
          Math.PI * 2,
        );
        ctx.fill();
      }
    }
    this.canvas.dataset.frame = f.join(",");
  }
}
window.FishSprite = FishSprite;
