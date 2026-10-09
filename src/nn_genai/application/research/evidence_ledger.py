from nn_genai.models.retrieved_evidence import RetrievedEvidence


class EvidenceLedger:
    def __init__(self) -> None:
        self._evidence: dict[str, RetrievedEvidence] = {}

    def add(self, evidence: RetrievedEvidence) -> None:
        existing = self._evidence.get(evidence.evidence_id)

        if existing and existing.url != evidence.url:
            raise ValueError(
                f"Evidence ID collision: {evidence.evidence_id}"
            )

        self._evidence[evidence.evidence_id] = evidence

    def get(self, evidence_id: str) -> RetrievedEvidence | None:
        return self._evidence.get(evidence_id)

    def all(self) -> list[RetrievedEvidence]:
        return list(self._evidence.values())
