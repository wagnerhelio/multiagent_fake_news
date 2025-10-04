#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import heapq
from typing import Dict, Any, List, Tuple

class SchedulerAgent:
    """
    Filas por FORMATO (texto, imagem, áudio, vídeo) com prioridade.
    Preempção: se capacidade cheia e entra item com prioridade muito maior,
    suspende o item ativo de menor prioridade e reencaminha para fila.
    """
    FORMATS = ["text", "image", "audio", "video"]

    def __init__(self, checking_units_capacity: int = 2, preemption_threshold: int = 2):
        self.capacity = checking_units_capacity
        self.preemption_threshold = preemption_threshold

        # Priority queues: heaps of tuples (-priority, counter, item)
        self.queues: Dict[str, List[Tuple[int,int,Dict[str,Any]]]] = {fmt: [] for fmt in self.FORMATS}
        self._counter = 0
        self.active_checks: List[Dict[str, Any]] = []
        self.preempted: Dict[str, Dict[str, Any]] = {}

    def add_content_to_queue(self, item: Dict[str, Any]):
        fmt = item.get("type", "text")
        if fmt not in self.queues:
            fmt = "text"
        # negative for max-heap behavior
        prio = int(item.get("overall_priority", 1))
        heapq.heappush(self.queues[fmt], (-prio, self._counter, item))
        self._counter += 1

    def _pull_highest_any(self) -> Dict[str, Any] | None:
        # Check tops of all format queues and return highest-priority item
        best = None
        best_key = None
        for fmt, q in self.queues.items():
            if not q:
                continue
            prio, cnt, it = q[0]
            if (best is None) or (prio < best[0]):  # remember prio is negative; lower is higher priority
                best = (prio, cnt, it); best_key = fmt
        if best is None:
            return None
        heapq.heappop(self.queues[best_key])
        return best[2]

    def _min_active(self) -> Dict[str, Any] | None:
        if not self.active_checks:
            return None
        return min(self.active_checks, key=lambda x: int(x.get("overall_priority", 0)))

    def _preempt_if_needed(self, new_item: Dict[str, Any]) -> bool:
        """Return True if preempted someone to make room for new_item."""
        if len(self.active_checks) < self.capacity:
            return False
        min_act = self._min_active()
        if not min_act:
            return False
        p_new = int(new_item.get("overall_priority", 1))
        p_min = int(min_act.get("overall_priority", 1))
        if p_new >= p_min * self.preemption_threshold:
            # Preempt the min active
            self.active_checks.remove(min_act)
            min_act["status"] = "preempted"
            self.preempted[min_act["id"]] = min_act
            self.add_content_to_queue(min_act)  # back to its format queue
            return True
        return False

    def dispatch(self) -> List[Dict[str, Any]]:
        """Fill capacity with highest-priority items; apply preemption if needed.
           Returns list of items dispatched now (moved to active)."""
        dispatched = []
        # First, try to fill vacancies
        while len(self.active_checks) < self.capacity:
            nxt = self._pull_highest_any()
            if not nxt: break
            nxt["status"] = "in_analysis"
            self.active_checks.append(nxt)
            dispatched.append(nxt)

        # Then, check if top queue item should preempt
        nxt = self._pull_highest_any()
        if nxt:
            if self._preempt_if_needed(nxt):
                # after preemption, we can push nxt into active
                nxt["status"] = "in_analysis"
                self.active_checks.append(nxt)
                dispatched.append(nxt)
            else:
                # put it back if not used now
                self.add_content_to_queue(nxt)
        return dispatched

    def mark_done(self, content_id: str):
        self.active_checks = [c for c in self.active_checks if c.get("id") != content_id]

    def get_queue_status(self) -> Dict[str, Any]:
        q_sizes = {fmt: len(q) for fmt, q in self.queues.items()}
        return {
            "queues": q_sizes,
            "active_checks": [c.get("id") for c in self.active_checks],
            "preempted": list(self.preempted.keys()),
            "capacity": self.capacity,
            "preemption_threshold": self.preemption_threshold,
        }
