import { useEffect, useState } from "react";

/** Animate a number counting up from 0 to target on mount (ease-out cubic).
 *  Returns null when target is not a finite number. */
export default function useCountUp(target, duration = 1200) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (!Number.isFinite(target)) return undefined;
    let raf;
    const start = performance.now();
    const tick = (now) => {
      const t = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setValue(target * eased);
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);

  return Number.isFinite(target) ? value : null;
}
