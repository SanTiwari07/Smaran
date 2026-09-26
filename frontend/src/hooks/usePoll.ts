import { useCallback, useEffect, useRef, useState } from "react";

// Poll every `ms` (default 1 s). Keeps the last good data when a request fails, so a
// device going down shows an error instead of blanking the view.
export function usePoll<T>(fn: () => Promise<T>, deps: unknown[] = [], ms = 1000) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fnRef = useRef(fn);
  fnRef.current = fn;

  const refresh = useCallback(async () => {
    try {
      setData(await fnRef.current());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    let alive = true;
    setData(null);
    const tick = async () => { if (alive) await refresh(); };
    tick();
    const id = setInterval(tick, ms);
    return () => { alive = false; clearInterval(id); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, ms, refresh]);

  return { data, error, refresh };
}
