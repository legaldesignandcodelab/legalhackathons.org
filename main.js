/* ============================================================
   Legal Hackathon @ HSG — Main JavaScript
   ============================================================ */

/* ── Boot Sequence ── */
(function () {
  const lines = [
    '> initializing legal_hackathon.exe...',
    '> loading modules: [AI, LLM, NLP, Legal]',
    '> connecting to UNISG network... OK',
    '> checking venue: Rosenbergstrasse 30... OK',
    '> setting date: November 7-8, 2026',
    '> allocating 24h of hacking time...',
    '> ready. welcome, hacker.',
    '',
  ];
  const el = document.getElementById('boot-text');
  let li = 0, ci = 0;

  function type() {
    if (li >= lines.length) {
      setTimeout(() => {
        document.getElementById('boot').classList.add('done');
        setTimeout(() => document.getElementById('boot').remove(), 600);
      }, 300);
      return;
    }
    if (ci <= lines[li].length) {
      el.textContent += lines[li][ci] || '';
      ci++;
      setTimeout(type, li === lines.length - 1 ? 100 : 20);
    } else {
      el.textContent += '\n';
      li++;
      ci = 0;
      setTimeout(type, 150);
    }
  }
  type();
})();

/* ── Matrix Rain ── */
(function () {
  const c = document.getElementById('matrix');
  const x = c.getContext('2d');
  let w, h, cols, drops;
  const chars = '01{}[]();:<>/=+-*&|!?#$%@ABCDEFabcdef'.split('');

  function resize() {
    w = c.width = window.innerWidth;
    h = c.height = window.innerHeight;
    cols = Math.floor(w / 18);
    drops = Array(cols).fill(1);
  }

  resize();
  window.addEventListener('resize', resize);

  function draw() {
    x.fillStyle = 'rgba(7,7,10,0.06)';
    x.fillRect(0, 0, w, h);
    x.fillStyle = 'rgba(0,255,136,0.3)';
    x.font = '13px JetBrains Mono';
    for (let i = 0; i < cols; i++) {
      const t = chars[Math.floor(Math.random() * chars.length)];
      x.fillText(t, i * 18, drops[i] * 18);
      if (drops[i] * 18 > h && Math.random() > 0.975) drops[i] = 0;
      drops[i]++;
    }
  }
  setInterval(draw, 55);
})();

/* ── Cursor Glow ── */
document.addEventListener('mousemove', e => {
  const g = document.getElementById('cursor-glow');
  g.style.left = e.clientX + 'px';
  g.style.top = e.clientY + 'px';
});

/* ── Parallax Floating Elements ── */
(function () {
  const layer = document.getElementById('parallax');
  const items = [];
  const brackets = ['{', '}', '[', ']', '()', '</>', '&&', '||', '===', 'fn()', 'if()'];

  for (let i = 0; i < 20; i++) {
    const d = document.createElement('div');
    d.className = 'p-dot';
    d.style.left = Math.random() * 100 + '%';
    d.style.top = Math.random() * 100 + '%';
    layer.appendChild(d);
    items.push({ el: d, speed: 0.2 + Math.random() * 0.4 });
  }
  for (let i = 0; i < 8; i++) {
    const l = document.createElement('div');
    l.className = 'p-line';
    l.style.left = Math.random() * 100 + '%';
    l.style.top = Math.random() * 100 + '%';
    layer.appendChild(l);
    items.push({ el: l, speed: 0.1 + Math.random() * 0.3 });
  }
  for (let i = 0; i < 10; i++) {
    const b = document.createElement('div');
    b.className = 'p-bracket';
    b.textContent = brackets[Math.floor(Math.random() * brackets.length)];
    b.style.left = Math.random() * 100 + '%';
    b.style.top = Math.random() * 100 + '%';
    layer.appendChild(b);
    items.push({ el: b, speed: 0.05 + Math.random() * 0.15 });
  }

  window.addEventListener('scroll', () => {
    const s = window.scrollY;
    items.forEach(i => { i.el.style.transform = 'translateY(' + (-s * i.speed) + 'px)'; });
  });
})();

/* ── Countdown Timer ── */
const countdownTarget = new Date('2026-11-07T10:00:00+01:00');

function tick() {
  const n = new Date();
  const d = countdownTarget - n;
  if (d <= 0) return;
  document.getElementById('cd-d').textContent = String(Math.floor(d / 864e5)).padStart(2, '0');
  document.getElementById('cd-h').textContent = String(Math.floor(d % 864e5 / 36e5)).padStart(2, '0');
  document.getElementById('cd-m').textContent = String(Math.floor(d % 36e5 / 6e4)).padStart(2, '0');
  document.getElementById('cd-s').textContent = String(Math.floor(d % 6e4 / 1e3)).padStart(2, '0');
}
tick();
setInterval(tick, 1000);

/* ── Typing Effect ── */
(function () {
  const words = ['law', 'future', 'code', 'justice'];
  let wi = 0, ci = 0, del = false;
  const el = document.getElementById('typed-text');

  function type() {
    const w = words[wi];
    if (!del) {
      el.textContent = w.substring(0, ci + 1);
      ci++;
      if (ci === w.length) { del = true; setTimeout(type, 2200); return; }
    } else {
      el.textContent = w.substring(0, ci - 1);
      ci--;
      if (ci === 0) { del = false; wi = (wi + 1) % words.length; setTimeout(type, 400); return; }
    }
    setTimeout(type, del ? 50 : 110);
  }
  type();
})();

/* ── Animated Stats Counters ── */
function animateCounters() {
  document.querySelectorAll('.stat-num[data-target]').forEach(el => {
    const t = +el.dataset.target;
    const pre = el.dataset.prefix || '';
    const suf = el.dataset.suffix || '';
    let cur = 0;
    const step = Math.ceil(t / 60);

    function count() {
      cur = Math.min(cur + step, t);
      el.textContent = pre + cur + suf;
      if (cur < t) requestAnimationFrame(count);
    }
    count();
  });
}

/* ── Scroll Reveal + Counter Trigger ── */
let countersTriggered = false;
const obs = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      e.target.classList.add('visible');
      if (e.target.classList.contains('stats-bar') && !countersTriggered) {
        countersTriggered = true;
        animateCounters();
      }
    }
  });
}, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

document.querySelectorAll('.reveal, .stats-bar').forEach(el => obs.observe(el));

/* ── Lazy Load Map ── */
const mapObs = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      e.target.innerHTML = `<iframe
        src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d2699.3303475434873!2d9.365943188063849!3d47.425001526184765!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x479b1e49898ebd9b%3A0x25559adad24043dc!2sRosenbergstrasse%2030%2C%209001%20St.%20Gallen!5e0!3m2!1sen!2sch!4v1776621735328!5m2!1sen!2sch"
        loading="lazy"
        referrerpolicy="no-referrer-when-downgrade"
        style="width:100%;height:100%;border:none;filter:grayscale(1) invert(1) contrast(0.8) brightness(0.7)">
      </iframe>`;
      mapObs.unobserve(e.target);
    }
  });
}, { rootMargin: '200px' });

const mapContainer = document.getElementById('map-container');
if (mapContainer) mapObs.observe(mapContainer);

/* ── Nav Scroll Effect ── */
window.addEventListener('scroll', () => {
  document.getElementById('nav').classList.toggle('scrolled', window.scrollY > 50);
});

/* ── FAQ Accordion ── */
document.querySelectorAll('.faq-q').forEach(btn => {
  btn.addEventListener('click', () => {
    const item = btn.parentElement;
    item.classList.toggle('open');
    btn.setAttribute('aria-expanded', item.classList.contains('open'));
  });
});

/* ── Smooth Scroll ── */
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    e.preventDefault();
    document.querySelector(a.getAttribute('href'))?.scrollIntoView({ behavior: 'smooth' });
    document.querySelector('.nav-links')?.classList.remove('open');
  });
});
