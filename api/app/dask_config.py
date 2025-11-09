from typing import Optional
import os
import warnings

class DaskConfig:
    """For bulk/offline jobs (e.g., CSV → Postgres seed, checks).

    Behavior:
    - If DASK_MODE is set to "remote", the code requires DASK_SCHEDULER_ADDRESS and connects to it.
    - If DASK_MODE is set to "local", the code always creates a LocalCluster.
    - If DASK_MODE is not set, fall back to the previous heuristic: use DASK_SCHEDULER_ADDRESS if present, otherwise LocalCluster.

    Env vars used:
    - DASK_MODE: optional, one of "local" or "remote" (case-insensitive)
    - DASK_SCHEDULER_ADDRESS: optional, address of a remote Dask scheduler (e.g., tcp://dask-scheduler:8786)
    - DASK_LOCAL_THREADS: optional int, 0 => auto (default)
    """
    def __init__(self):
        # explicit mode: 'local' or 'remote' (case-insensitive). If empty, use heuristic.
        self.mode = (os.getenv("DASK_MODE") or "").strip().lower()
        self.scheduler_address: Optional[str] = os.getenv("DASK_SCHEDULER_ADDRESS") or None
        # number of threads per worker; 0 => auto (None -> use default behavior)
        try:
            self.local_threads: int = int(os.getenv("DASK_LOCAL_THREADS", "0"))  # 0 => auto
        except ValueError:
            warnings.warn("Invalid DASK_LOCAL_THREADS value; falling back to 0 (auto)")
            self.local_threads = 0

    def client(self):
        # Local import to keep startup light unless needed
        from distributed import Client, LocalCluster

        # Explicit remote mode: require scheduler address
        if self.mode == "remote":
            if not self.scheduler_address:
                raise RuntimeError("DASK_MODE=remote but DASK_SCHEDULER_ADDRESS is not set")
            return Client(self.scheduler_address)

        # Explicit local mode
        if self.mode == "local":
            threads = None if self.local_threads == 0 else self.local_threads
            cluster = LocalCluster(n_workers=0 if self.local_threads == 0 else 1,
                                   threads_per_worker=threads)
            return Client(cluster)

        # Fallback heuristic (backwards compatible): prefer scheduler address if set
        if self.scheduler_address:
            # warn that remote address is being used implicitly
            warnings.warn("Using DASK_SCHEDULER_ADDRESS implicitly (set DASK_MODE=remote to be explicit)")
            return Client(self.scheduler_address)

        # Default: local cluster
        threads = None if self.local_threads == 0 else self.local_threads
        cluster = LocalCluster(n_workers=0 if self.local_threads == 0 else 1,
                               threads_per_worker=threads)
        return Client(cluster)
