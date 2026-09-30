// Red Horizon art, all drawn in code: starfield, layered Martian horizon, the astronaut and helmet.
// No raster images anywhere. Decorative pieces are aria-hidden.
import { useEffect, useRef } from "react";

/** Twinkling parallax stars on a fixed canvas behind the page. Freezes for reduced motion. */
export function Starfield({ dim = false }: { dim?: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const cv = ref.current;
    const cx = cv?.getContext("2d");
    if (!cv || !cx) return;
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let stars: { x: number; y: number; r: number; p: number; d: number }[] = [];
    const size = () => {
      cv.width = window.innerWidth;
      cv.height = window.innerHeight;
      stars = Array.from({ length: 140 }, () => ({
        x: Math.random() * cv.width, y: Math.random() * cv.height * 0.75,
        r: Math.random() * 1.3 + 0.3, p: Math.random() * 6, d: Math.random(),
      }));
    };
    size();
    window.addEventListener("resize", size);
    let timer = 0;
    const draw = () => {
      cx.clearRect(0, 0, cv.width, cv.height);
      const t = still ? 0 : Date.now() / 1000;
      for (const s of stars) {
        const x = (((s.x - t * 3 * s.d) % cv.width) + cv.width) % cv.width;
        cx.globalAlpha = (0.3 + 0.4 * Math.abs(Math.sin(t * 0.8 + s.p))) * (1 - s.y / (cv.height * 0.9));
        cx.fillStyle = "#f5f1ea";
        cx.beginPath();
        cx.arc(x, s.y, s.r, 0, 7);
        cx.fill();
      }
      if (!still) timer = window.setTimeout(() => requestAnimationFrame(draw), document.hidden ? 500 : 0);
    };
    draw();
    return () => { window.removeEventListener("resize", size); clearTimeout(timer); };
  }, []);
  return (
    <canvas ref={ref} aria-hidden="true"
      className={`pointer-events-none fixed inset-0 -z-10 h-full w-full transition-opacity duration-700 ${dim ? "opacity-100" : "opacity-60"}`} />
  );
}

/** The Horizon Rule: four depth planes of Martian ground. Every page ends its header with it. */
export function Horizon({ className = "", height = 140 }: { className?: string; height?: number }) {
  return (
    <svg className={className} viewBox="0 0 1440 300" preserveAspectRatio="none" height={height} width="100%" aria-hidden="true">
      <path d="M0 120 L120 96 L200 118 L330 84 L470 122 L560 100 L700 130 L860 90 L1000 124 L1140 92 L1300 118 L1440 100 V300 H0Z" fill="#5a1f12" />
      <path d="M0 170 Q180 120 360 165 T720 160 T1080 150 T1440 165 V300 H0Z" fill="#8a2f12" />
      <path d="M0 215 Q220 170 440 210 T900 205 T1440 200 V300 H0Z" fill="#c1440e" />
      <path d="M0 255 Q300 225 620 255 T1440 245 V300 H0Z" fill="#7a2a12" />
      <g fill="#3a1508">
        <ellipse cx="180" cy="262" rx="46" ry="16" /><ellipse cx="260" cy="270" rx="26" ry="9" />
        <ellipse cx="1180" cy="258" rx="60" ry="18" /><ellipse cx="1290" cy="272" rx="30" ry="10" />
      </g>
    </svg>
  );
}

/** Two moons drifting across the sky, very slowly. */
export function Moons() {
  return (
    <>
      <span aria-hidden="true" className="pointer-events-none absolute left-0 top-10 h-[22px] w-[22px] rounded-full opacity-80"
        style={{ background: "radial-gradient(circle at 35% 35%,#e9d3bd,#8b6a55)", animation: "drift 90s linear infinite" }} />
      <span aria-hidden="true" className="pointer-events-none absolute left-0 top-24 h-3 w-3 rounded-full opacity-70"
        style={{ background: "radial-gradient(circle at 35% 35%,#e9d3bd,#8b6a55)", animation: "drift 140s linear infinite -50s" }} />
    </>
  );
}

/** Faceless astronaut planting a flag. `letter` is the patch on the suit. */
export function AstronautFlag({ letter = "A", className = "" }: { letter?: string; className?: string }) {
  return (
    <svg viewBox="0 0 200 300" className={className} aria-hidden="true">
      <line x1="150" y1="20" x2="150" y2="285" stroke="#b9afa6" strokeWidth="3" />
      <path d="M150 22h40l-8 14 8 14h-40z" fill="#c1440e" />
      <ellipse cx="100" cy="288" rx="60" ry="8" fill="#000" opacity=".3" />
      <rect x="52" y="120" width="38" height="66" rx="14" fill="#b9afa6" />
      <rect x="66" y="110" width="66" height="96" rx="24" fill="#f5f1ea" />
      <rect x="86" y="160" width="26" height="14" rx="3" fill="#c1440e" />
      <text x="99" y="171" fontSize="10" textAnchor="middle" fill="#f5f1ea" fontFamily="JetBrains Mono" fontWeight="500">{letter}</text>
      <rect x="70" y="200" width="24" height="76" rx="10" fill="#f5f1ea" /><rect x="104" y="200" width="24" height="76" rx="10" fill="#f5f1ea" />
      <rect x="66" y="266" width="32" height="16" rx="6" fill="#c1440e" /><rect x="102" y="266" width="32" height="16" rx="6" fill="#c1440e" />
      <path d="M124 128Q154 118 152 96" stroke="#f5f1ea" strokeWidth="20" strokeLinecap="round" fill="none" />
      <circle cx="99" cy="80" r="44" fill="#f5f1ea" stroke="#b9afa6" strokeWidth="2" />
      <rect x="68" y="58" width="62" height="44" rx="22" fill="#1a1216" />
      <path d="M72 92Q99 72 126 92" stroke="#e8590c" strokeWidth="3" fill="none" opacity=".8" />
      <circle cx="86" cy="70" r="4" fill="#fff" opacity=".7" />
    </svg>
  );
}

/** Compact helmet glyph for device cards. The visor takes the colour of the link state. */
export function Helmet({ size = 40, visor = "#3de0e6", patch = "#c1440e" }: { size?: number; visor?: string; patch?: string }) {
  return (
    <svg viewBox="0 0 48 48" width={size} height={size} className="shrink-0" aria-hidden="true">
      <circle cx="24" cy="24" r="20" fill="#f5f1ea" />
      <rect x="10" y="14" width="28" height="20" rx="10" fill={visor} opacity=".9" />
      <rect x="10" y="14" width="28" height="20" rx="10" fill="#1a1216" opacity=".38" />
      <path d="M14 30Q24 22 34 30" stroke="#e8590c" strokeWidth="2" fill="none" />
      <path d="M13 21Q16 17 22 16" stroke="#fff" strokeOpacity=".55" strokeWidth="2" fill="none" strokeLinecap="round" />
      <circle cx="24" cy="24" r="20" fill="none" stroke="#b9afa6" strokeWidth="1.5" />
      <rect x="19" y="42" width="10" height="4" rx="1.5" fill={patch} />
    </svg>
  );
}
