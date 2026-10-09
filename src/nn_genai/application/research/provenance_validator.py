from nn_genai.application.research.evidence_ledger import EvidenceLedger
from nn_genai.models.research_draft import ResearchDraft, ResearchStatus
from nn_genai.models.research_result import (
    ResearchResult,
    ResearchSource,
)
from nn_genai.application.research.errors import (
    InsufficientEvidenceError,
    InvalidEvidenceReferenceError,
)


class ProvenanceValidator:
    def build_result(
        self,
        draft: ResearchDraft,
        ledger: EvidenceLedger,
    ) -> ResearchResult:
        if draft.status is ResearchStatus.CONCLUSIVE and not ledger.all():
            raise InsufficientEvidenceError(
                "The research produced no retrievable evidence."
            )

        sources: list[ResearchSource] = []
        seen_ids: set[str] = set()

        for citation in draft.citations:
            if citation.evidence_id in seen_ids:
                continue

            evidence = ledger.get(citation.evidence_id)

            if evidence is None:
                raise InvalidEvidenceReferenceError(
                    "The model cited evidence that was not returned "
                    f"by search: {citation.evidence_id}"
                )

            seen_ids.add(citation.evidence_id)

            sources.append(
                ResearchSource(
                    title=evidence.title,
                    url=str(evidence.url),
                    supporting_claim=citation.supporting_claim,
                )
            )

        if draft.status is ResearchStatus.CONCLUSIVE and not sources:
            raise InsufficientEvidenceError(
                "No valid evidence supports the research conclusion."
            )

        return ResearchResult(
            person_name=draft.person_name,
            selected_work=draft.selected_work,
            reasoning=draft.reasoning,
            status=draft.status,
            sources=sources,
            confidence=draft.confidence,
        )
