document.addEventListener('DOMContentLoaded', () => {
  if (window.__sehatWargaMainInitialized) return;
  window.__sehatWargaMainInitialized = true;
  const nav = document.getElementById('site-navigation');
  const toggle = document.getElementById('nav-toggle');
  const close = document.getElementById('nav-close');
  const overlay = document.getElementById('nav-overlay');
  const backgrounds = [document.querySelector('main'), document.querySelector('footer'), document.querySelector('.navbar-brand'), toggle];
  const mobile = window.matchMedia('(max-width:1023px)');
  function setOpen(open) {
    nav.classList.toggle('is-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    document.body.classList.toggle('nav-open', open);
    overlay.hidden = !open;
    backgrounds.forEach(el => { if(el) el.inert = open; });
    if(open) { nav.setAttribute('role','dialog'); nav.setAttribute('aria-modal','true'); requestAnimationFrame(() => { if(nav.classList.contains('is-open')) close.focus(); }); }
    else { nav.removeAttribute('role'); nav.removeAttribute('aria-modal'); if(mobile.matches) toggle.focus(); }
  }
  toggle.addEventListener('click', () => setOpen(!nav.classList.contains('is-open')));
  close.addEventListener('click', () => setOpen(false));
  overlay.addEventListener('click', () => setOpen(false));
  mobile.addEventListener('change', () => setOpen(false));
  nav.addEventListener('click', e => { if(mobile.matches && e.target.closest('a')) setOpen(false); });
  document.addEventListener('keydown', e => {
    if(e.key === 'Escape') {
      if(nav.classList.contains('is-open')) setOpen(false);
      document.querySelectorAll('.nav-dropdown[open]').forEach(d => { d.open=false; d.querySelector('summary').focus(); });
    }
    if(e.key === 'Tab' && nav.classList.contains('is-open')) {
      const focusable = [...nav.querySelectorAll('a,button,input:not([type="hidden"]),summary')].filter(el => el.getClientRects().length && getComputedStyle(el).visibility === 'visible' && !el.disabled && !el.closest('details:not([open]) .dropdown-panel'));
      if(!focusable.length) { e.preventDefault(); return; }
      const first=focusable[0], last=focusable[focusable.length-1];
      if(!nav.contains(document.activeElement)) { e.preventDefault(); (e.shiftKey ? last : first).focus(); }
      else if(e.shiftKey && document.activeElement===first) { e.preventDefault(); last.focus(); }
      else if(!e.shiftKey && document.activeElement===last) { e.preventDefault(); first.focus(); }
    }
  });
  document.addEventListener('click', e => document.querySelectorAll('.nav-dropdown[open]').forEach(d => { if(!d.contains(e.target)) d.open=false; }));
  document.querySelectorAll('.data-table').forEach(table => {
    const headers=[...table.querySelectorAll('thead th')].map(h=>h.textContent.trim());
    table.classList.add('mobile-cards');
    table.querySelectorAll('tbody tr').forEach(row=> [...row.children].forEach((cell,i)=> {cell.dataset.label=headers[i] || ''; }));
  });
  document.querySelectorAll('.form-group').forEach((group,i) => {
    const field=group.querySelector('input:not([type="hidden"]),select,textarea');
    if(!field) return;
    const label=group.querySelector('label');
    field.id ||= `field-${i}`;
    if(label && !label.htmlFor) label.htmlFor=field.id;
    const descriptions=[...group.querySelectorAll('.form-error,.form-hint')];
    descriptions.forEach((el,j)=>{ el.id ||= `${field.id}-hint-${j}`; if(el.classList.contains('form-error')) el.setAttribute('role','alert'); });
    if(descriptions.length) field.setAttribute('aria-describedby',descriptions.map(el=>el.id).join(' '));
    if(group.querySelector('.form-error')) field.setAttribute('aria-invalid','true');
  });
  document.querySelectorAll('form[method="POST"]').forEach(form => form.addEventListener('submit',e=> {
    if(e.defaultPrevented) return;
    if(form.dataset.submitting) { e.preventDefault(); return; }
    form.dataset.submitting='true'; form.setAttribute('aria-busy','true');
    // Keep named submit controls enabled so their values still reach the server.
    form.querySelectorAll('button[type="submit"]').forEach(button=> { if(!button.name) {button.disabled=true; button.dataset.label=button.textContent; button.textContent='Memproses…';} });
  }));
  window.addEventListener('pageshow',()=>document.querySelectorAll('form[data-submitting]').forEach(form=> {delete form.dataset.submitting; form.removeAttribute('aria-busy'); form.querySelectorAll('button[data-label]').forEach(b=>{b.disabled=false;b.textContent=b.dataset.label;});}));

  // Coalesce high-frequency input. All geometry reads precede style writes.
  const frameJobs = new Map();
  let inputFrame = 0;
  let frameBounds = new Map();
  const boundsFor = element => {
    if (!frameBounds.has(element)) frameBounds.set(element, element.getBoundingClientRect());
    return frameBounds.get(element);
  };
  const flushInput = () => {
    inputFrame = 0;
    frameBounds = new Map();
    const jobs = [...frameJobs.values()];
    frameJobs.clear();
    const writes = jobs.map(read => read());
    writes.forEach(write => { if (write) write(); });
    frameBounds.clear();
  };
  const scheduleInput = (key, read) => {
    frameJobs.set(key, read);
    if (!document.hidden && !inputFrame) inputFrame = requestAnimationFrame(flushInput);
  };
  const pointerEffect = (element, read, reset) => {
    const key = {};
    element.addEventListener('pointermove', event => {
      scheduleInput(key, () => read(event));
    }, { passive: true });
    if (reset) element.addEventListener('pointerleave', () => {
      frameJobs.delete(key);
      reset();
    });
  };
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      cancelAnimationFrame(inputFrame);
      inputFrame = 0;
    } else if (frameJobs.size && !inputFrame) inputFrame = requestAnimationFrame(flushInput);
  });

  // Visual motion is progressive enhancement: content remains visible without JS.
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const progressBar = document.getElementById('scroll-progress-bar');
  const updateProgress = () => {
    if (!progressBar) return;
    const scrollable = document.documentElement.scrollHeight - window.innerHeight;
    const progress = scrollable > 0 ? Math.min(1, window.scrollY / scrollable) : 0;
    return () => { progressBar.style.transform = `scaleX(${progress})`; };
  };
  window.addEventListener('scroll', () => {
    scheduleInput(progressBar, updateProgress);
  }, { passive: true });
  updateProgress()?.();

  // Keep the journey reveal independent of other sections' animation order.
  if (!reducedMotion.matches && 'IntersectionObserver' in window) {
    const journeyObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    document.querySelectorAll('.journey-step').forEach(card => {
      card.classList.add('journey-reveal');
      journeyObserver.observe(card);
    });
  }

  const revealTargets = document.querySelectorAll([
    '.service-tile', '.feature-card', '.steps-grid li', '.facility-spotlight .split-panel',
    '.final-cta', '.dashboard-header', '.summary-panel', '.stat-card', '.action-card',
    '.secondary-details', '.table-responsive', '.profile-card', '.facility-card', '.auth-card'
  ].join(','));
  if (!reducedMotion.matches && 'IntersectionObserver' in window) {
    document.documentElement.classList.add('reveal-ready');
    revealTargets.forEach((element, index) => {
      element.classList.add('reveal-item');
      element.style.setProperty('--reveal-delay', `${Math.min(index % 4, 3) * 65}ms`);
    });
    const revealObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.09, rootMargin: '0px 0px -30px' });
    revealTargets.forEach(element => revealObserver.observe(element));
  }

  const finePointer = window.matchMedia('(pointer: fine)').matches;
  const ambientWorld = document.getElementById('ambient-world');
  if (ambientWorld && finePointer && !reducedMotion.matches) {
    pointerEffect(document, event => {
      const ambientX = event.clientX / window.innerWidth * 100;
      const ambientY = event.clientY / window.innerHeight * 100;
      return () => {
        document.body.style.setProperty('--bg-pointer-x', `${ambientX.toFixed(1)}%`);
        document.body.style.setProperty('--bg-pointer-y', `${ambientY.toFixed(1)}%`);
        ambientWorld.style.setProperty('--ambient-shift-x', `${((ambientX - 50) * .08).toFixed(2)}px`);
        ambientWorld.style.setProperty('--ambient-shift-y', `${((ambientY - 50) * .06).toFixed(2)}px`);
      };
    });
  }

  const tiltTargets = document.querySelectorAll([
    '[data-tilt]',
    '.stat-card',
    '.action-card',
    '.profile-card',
    '.auth-card',
    '.service-tile',
    '.secondary-details'
  ].join(','));
    tiltTargets.forEach(card => {
    if (reducedMotion.matches || !finePointer) return;
    card.classList.add('fx-tilt');
    pointerEffect(card, event => {
      const bounds = boundsFor(card);
      const x = (event.clientX - bounds.left) / bounds.width - 0.5;
      const y = (event.clientY - bounds.top) / bounds.height - 0.5;
      const intensity = card.matches('.health-orbit,.mini-map') ? 10 : 5;
      return () => {
      card.style.setProperty('--tilt-x', `${(-y * intensity).toFixed(2)}deg`);
      card.style.setProperty('--tilt-y', `${(x * intensity).toFixed(2)}deg`);
      card.style.setProperty('--spot-x', `${((x + .5) * 100).toFixed(1)}%`);
      card.style.setProperty('--spot-y', `${((y + .5) * 100).toFixed(1)}%`);
      };
    }, () => {
      card.style.setProperty('--tilt-x', '0deg');
      card.style.setProperty('--tilt-y', '0deg');
    });
  });

  // Magnetic primary actions. The displacement is intentionally small enough
  // that the target never escapes the pointer or changes the document layout.
/* Magnetic primary actions.
   Tombol di dalam facility card dikecualikan agar klik detail stabil. */
  if (!reducedMotion.matches && finePointer) {
    document
      .querySelectorAll('.btn-primary, .assistant-floating-btn')
      .forEach(button => {

        /* Jangan gunakan magnetic effect pada tombol fasilitas */
        if (button.closest('.facility-card')) {
          return;
        }

        button.classList.add('fx-magnetic');

        pointerEffect(button, event => {
          const bounds = boundsFor(button);

          const x =
            event.clientX -
            bounds.left -
            bounds.width / 2;

          const y =
            event.clientY -
            bounds.top -
            bounds.height / 2;

          return () => {
          button.style.setProperty(
            '--magnetic-x',
            `${(x * .11).toFixed(1)}px`
          );

          button.style.setProperty(
            '--magnetic-y',
            `${(y * .14).toFixed(1)}px`
          );
          };
        }, () => {
          button.style.setProperty('--magnetic-x', '0px');
          button.style.setProperty('--magnetic-y', '0px');
        });

      });
  }

  const addEnergyShards = (surface, amount) => {
    if (!surface || reducedMotion.matches) return;
    surface.classList.add('fx-energy-field');
    const layer = document.createElement('div');
    layer.className = 'energy-shards';
    layer.setAttribute('aria-hidden', 'true');
    for (let index = 0; index < amount; index += 1) {
      const shard = document.createElement('i');
      shard.style.setProperty('--x', `${8 + ((index * 19) % 86)}%`);
      shard.style.setProperty('--y', `${7 + ((index * 31) % 88)}%`);
      shard.style.setProperty('--size', `${4 + (index % 5) * 2}px`);
      shard.style.setProperty('--delay', `${-(index * .43)}s`);
      shard.style.setProperty('--duration', `${5 + (index % 6) * .8}s`);
      shard.style.setProperty('--shard-color', ['var(--color-accent)','var(--color-blue)','var(--color-coral)','var(--color-amber)','var(--color-violet)'][index % 5]);
      layer.appendChild(shard);
    }
    surface.prepend(layer);
  };
  addEnergyShards(document.querySelector('.hero-section'), 18);
  addEnergyShards(document.querySelector('.steps-section'), 12);
  document.querySelectorAll('.summary-panel').forEach(panel => addEnergyShards(panel, 8));

  // Lightweight particle network for the public hero. It pauses automatically
  // when the hero leaves the viewport and caps pixel density for modest GPUs.
  const hero = document.querySelector('.hero-section');
  if (hero && !reducedMotion.matches) {
    const canvas = document.createElement('canvas');
    canvas.className = 'motion-canvas';
    canvas.setAttribute('aria-hidden', 'true');
    hero.prepend(canvas);
    const context = canvas.getContext('2d', { alpha: true });
    const particleColors = ['12,155,135','50,117,216','233,103,90','231,166,43','115,89,201'];
    let particles = [];
    let intersecting = true;
    let active = !document.hidden;
    let width = 0;
    let height = 0;
    let canvasFrame = 0;
    let pointerX = .5;
    let pointerY = .5;
    const resizeCanvas = () => {
      const bounds = hero.getBoundingClientRect();
      const ratio = Math.min(window.devicePixelRatio || 1, 1.5);
      canvas.width = Math.max(1, Math.round(bounds.width * ratio));
      canvas.height = Math.max(1, Math.round(bounds.height * ratio));
      canvas.style.width = `${bounds.width}px`;
      canvas.style.height = `${bounds.height}px`;
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      width = canvas.clientWidth;
      height = canvas.clientHeight;
      const count = Math.min(56, Math.max(26, Math.round(bounds.width / 28)));
      particles = Array.from({ length: count }, (_, index) => ({
        x: Math.random() * bounds.width,
        y: Math.random() * bounds.height,
        vx: (Math.random() - .5) * .28,
        vy: (Math.random() - .5) * .28,
        radius: 1.2 + Math.random() * 2.6,
        color: particleColors[index % particleColors.length]
      }));
    };
    const drawNetwork = () => {
      if (!active) { canvasFrame = 0; return; }
      context.clearRect(0, 0, width, height);
      particles.forEach((particle, index) => {
        particle.x += particle.vx + (pointerX - .5) * .055;
        particle.y += particle.vy + (pointerY - .5) * .04;
        if (particle.x < -20) particle.x = width + 20;
        if (particle.x > width + 20) particle.x = -20;
        if (particle.y < -20) particle.y = height + 20;
        if (particle.y > height + 20) particle.y = -20;
        context.beginPath();
        context.arc(particle.x, particle.y, particle.radius, 0, Math.PI * 2);
        context.fillStyle = `rgba(${particle.color},.34)`;
        context.fill();
        for (let otherIndex = index + 1; otherIndex < particles.length; otherIndex += 1) {
          const other = particles[otherIndex];
          const dx = particle.x - other.x;
          const dy = particle.y - other.y;
          if (Math.abs(dx) > 112 || Math.abs(dy) > 112) continue;
          const distance = Math.hypot(dx, dy);
          if (distance > 112) continue;
          context.beginPath();
          context.moveTo(particle.x, particle.y);
          context.lineTo(other.x, other.y);
          context.strokeStyle = `rgba(12,155,135,${.09 * (1 - distance / 112)})`;
          context.lineWidth = .7;
          context.stroke();
        }
      });
      canvasFrame = requestAnimationFrame(drawNetwork);
    };
    pointerEffect(hero, event => {
      const bounds = boundsFor(hero);
      return () => {
      pointerX = (event.clientX - bounds.left) / bounds.width;
      pointerY = (event.clientY - bounds.top) / bounds.height;
      hero.style.setProperty('--hero-pointer-x', `${pointerX * 100}%`);
      hero.style.setProperty('--hero-pointer-y', `${pointerY * 100}%`);
      };
    });
    const syncCanvas = () => {
      active = intersecting && !document.hidden;
      if (!active) {
        cancelAnimationFrame(canvasFrame);
        canvasFrame = 0;
      } else if (!canvasFrame) canvasFrame = requestAnimationFrame(drawNetwork);
    };
    if ('IntersectionObserver' in window) {
      const visibilityObserver = new IntersectionObserver(entries => {
        intersecting = entries[0].isIntersecting;
        syncCanvas();
      }, { threshold: 0 });
      visibilityObserver.observe(hero);
    }
    document.addEventListener('visibilitychange', syncCanvas);
    window.addEventListener('resize', () => {
      scheduleInput(canvas, () => () => resizeCanvas());
    }, { passive: true });
    resizeCanvas();
    drawNetwork();
  }

  // Suspend only repeating CSS animations; retain their timeline and keyframes.
  // Finite entrances and user-triggered transitions keep their existing behavior.
  if ('IntersectionObserver' in window && document.getAnimations) {
    const groups = new Map();
    const tracked = new WeakSet();
    const ownedPauses = new WeakSet();
    const syncGroup = (element, group) => {
      if (!element.isConnected) {
        observer.unobserve(element);
        groups.delete(element);
        return;
      }
      group.animations.forEach(animation => {
        if (animation.playState === 'idle' || animation.playState === 'finished') {
          group.animations.delete(animation);
          return;
        }
        if (document.hidden || !group.visible) {
          if (animation.playState === 'running') {
            animation.pause();
            ownedPauses.add(animation);
          }
        } else if (ownedPauses.has(animation)) {
          ownedPauses.delete(animation);
          animation.play();
        }
      });
    };
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        const group = groups.get(entry.target);
        if (!group) return;
        group.visible = entry.isIntersecting;
        syncGroup(entry.target, group);
      });
    }, { threshold: 0 });
    const trackAnimations = animations => {
      animations.forEach(animation => {
        if (tracked.has(animation) || animation.effect?.getTiming().iterations !== Infinity) return;
        const target = animation.effect.target;
        if (!(target instanceof Element)) return;
        // Observe the containing scene so moving decorations cannot pause themselves.
        const element = target.closest('.ambient-world,section,.summary-panel,.dashboard-header,.auth-card') || target;
        let group = groups.get(element);
        if (!group) {
          group = { visible: true, animations: new Set() };
          groups.set(element, group);
          observer.observe(element);
        }
        tracked.add(animation);
        group.animations.add(animation);
        syncGroup(element, group);
      });
    };
    trackAnimations(document.getAnimations());
    document.addEventListener('animationstart', event => {
      trackAnimations(event.target.getAnimations());
    });
    document.addEventListener('visibilitychange', () => groups.forEach((group, element) => syncGroup(element, group)));
  }

});
