"""Bound a decoded map observation to one owned debugger pause transaction.

No launch, input or target-memory writes occur here. The caller supplies an
already authenticated PauseClient and retained read callback. A returned
snapshot describes the past paused interval; it does not authorize a click.
"""
from copy import deepcopy

import ordinary_map_observation as decoder
from ordinary_map_pause_client import PauseClient, LeaseError


class ObservationSession:
    def __init__(self, client, read_exact, *, candidate, stack_indices=None):
        if not isinstance(client, PauseClient) or not callable(read_exact):
            raise TypeError('Owned PauseClient and exact-read callback required')
        self.client = client
        self.read_exact = read_exact
        self.candidate = deepcopy(candidate)
        self.identity = deepcopy(client.identity)
        self.stack_indices = None if stack_indices is None else tuple(stack_indices)
        self.sequence = 0
        self._reading = False

    def read(self):
        """Return one checked snapshot only after a matching successful resume."""
        if self._reading:
            raise LeaseError('Nested observation transactions are forbidden')
        if self.client.identity != self.identity:
            raise LeaseError('Observation session target identity changed')
        self._reading = True
        self.sequence += 1  # Failed observations also consume their sequence.
        try:
            with self.client.paused() as lease:
                paused = deepcopy(self.client.receipts[-1])
                result = decoder.observe(
                    self.read_exact, candidate=self.candidate,
                    identity=self.identity, sequence=self.sequence,
                    lease=lease, check_lease=self.client.check_lease,
                    stack_indices=self.stack_indices)
            resumed = deepcopy(self.client.receipts[-1])
            return dict(result, host_transaction=dict(paused=paused, resumed=resumed))
        finally:
            self._reading = False
