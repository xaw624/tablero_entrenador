import { createContext, useCallback, useContext, useState } from "react";
import { api } from "../api.js";

const StoreContext = createContext(null);

export function StoreProvider({ children }) {
  const [me, setMe] = useState(null);
  const [ready, setReady] = useState(false); // datos iniciales cargados
  const [patterns, setPatterns] = useState([]);
  const [levels, setLevels] = useState([]);
  const [athletes, setAthletes] = useState([]);
  const [routines, setRoutines] = useState({});
  const [tests, setTests] = useState([]);
  const [sessions, setSessions] = useState([]);

  const refreshLevels = useCallback(async () => {
    setLevels(await api.get("/api/levels"));
  }, []);
  const refreshAthletes = useCallback(async () => {
    setAthletes(await api.get("/api/athletes"));
  }, []);
  const refreshRoutines = useCallback(async () => {
    setRoutines(await api.get("/api/routines"));
  }, []);
  const refreshTests = useCallback(async () => {
    setTests(await api.get("/api/tests"));
  }, []);
  const refreshSessions = useCallback(async () => {
    setSessions(await api.get("/api/sessions"));
  }, []);

  const loadAll = useCallback(async () => {
    const [p, lv, a, r, t, s] = await Promise.all([
      api.get("/api/patterns"),
      api.get("/api/levels"),
      api.get("/api/athletes"),
      api.get("/api/routines"),
      api.get("/api/tests"),
      api.get("/api/sessions"),
    ]);
    setPatterns(p);
    setLevels(lv);
    setAthletes(a);
    setRoutines(r);
    setTests(t);
    setSessions(s);
    setReady(true);
  }, []);

  const reset = useCallback(() => {
    setMe(null);
    setReady(false);
    setPatterns([]);
    setLevels([]);
    setAthletes([]);
    setRoutines({});
    setTests([]);
    setSessions([]);
  }, []);

  const value = {
    me, setMe,
    ready,
    patterns, levels, athletes, routines, tests, sessions,
    loadAll, reset,
    refreshLevels, refreshAthletes, refreshRoutines, refreshTests, refreshSessions,
  };
  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore() {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error("useStore fuera de StoreProvider");
  return ctx;
}
