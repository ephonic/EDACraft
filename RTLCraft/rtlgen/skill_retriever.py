"""
rtlgen.skill_retriever — Skill-Guided RTL Generation: Retrieval Engine

Loads skills_index.yaml and retrieves relevant design patterns/modules
based on multi-dimensional query overlap.

Reference: skills/skills-guided-gen.md Section 5.2
"""
from __future__ import annotations

import os
import yaml
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class RetrievalQuery:
    """Query constructed from PE + task + behavior requirements."""
    target_module: str = ""
    pe_type: str = ""
    behavior_tags: List[str] = field(default_factory=list)
    interface_patterns: List[str] = field(default_factory=list)
    control_patterns: List[str] = field(default_factory=list)
    datapath_patterns: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    generation_goal: List[str] = field(default_factory=list)

    def all_tags(self) -> Set[str]:
        return set(
            self.behavior_tags
            + self.interface_patterns
            + self.control_patterns
            + self.datapath_patterns
            + self.keywords
        )


@dataclass
class ReferenceCard:
    """Reference card returned by SkillRetriever."""
    skill_id: str
    name: str
    relevance: float
    source_file: str
    source_class: str
    kind: str  # module | pattern
    domain: str
    why_relevant: List[str] = field(default_factory=list)
    useful_ideas: List[str] = field(default_factory=list)
    reusable_patterns: List[str] = field(default_factory=list)
    suggested_adaptation: List[str] = field(default_factory=list)
    caution: List[str] = field(default_factory=list)
    summary: str = ""
    behavior_tags: List[str] = field(default_factory=list)
    interface_patterns: List[str] = field(default_factory=list)
    control_patterns: List[str] = field(default_factory=list)
    datapath_patterns: List[str] = field(default_factory=list)


def _overlap_score(query_items: List[str], skill_items: List[str]) -> float:
    """Jaccard-like overlap score: |intersection| / |query|."""
    if not query_items:
        return 0.0
    qset = set(query_items)
    sset = set(skill_items)
    inter = qset & sset
    return len(inter) / len(qset)


def _keyword_score(query: RetrievalQuery, skill: Dict[str, Any]) -> float:
    """Simple keyword matching on skill name, summary, id, and sub_module keywords."""
    if not query.keywords:
        return 0.0
    sub_kw = []
    for sm in skill.get("sub_modules", []):
        sub_kw.extend(sm.get("keywords", []))
        sub_kw.extend(sm.get("behavior_tags", []))
    text = " ".join([
        skill.get("id", ""),
        skill.get("source", {}).get("class", ""),
        skill.get("summary", ""),
    ] + sub_kw).lower()
    qset = set(k.lower() for k in query.keywords)
    hits = sum(1 for k in qset if k in text)
    return hits / len(qset)


def _maturity_score(skill: Dict[str, Any]) -> float:
    """Score based on maturity metadata."""
    m = skill.get("maturity", {})
    score = 0.0
    if m.get("syntax_checked"):
        score += 0.3
    if m.get("sim_tested"):
        score += 0.4
    if m.get("synthesizable_likely"):
        score += 0.3
    return score


def _sub_module_score(query: RetrievalQuery, skill: Dict[str, Any]) -> float:
    """Score sub_modules within a skill entry. Returns best sub_module match."""
    sub_modules = skill.get("sub_modules", [])
    if not sub_modules:
        return 0.0

    best_score = 0.0
    for sub in sub_modules:
        sub_behavior = sub.get("behavior_tags", [])
        sub_keywords = sub.get("keywords", [])

        # Behavior tag overlap
        behav_score = _overlap_score(query.behavior_tags, sub_behavior)

        # Keyword overlap with sub_module keywords
        kw_score = 0.0
        if query.keywords and sub_keywords:
            qset = set(k.lower() for k in query.keywords)
            kw_text = " ".join(sub_keywords).lower()
            hits = sum(1 for k in qset if k in kw_text)
            kw_score = hits / len(qset)

        score = 0.4 * behav_score + 0.3 * kw_score
        if score > best_score:
            best_score = score

    return best_score


class SkillRetriever:
    """Retrieves relevant skills from a YAML index."""

    def __init__(self, index_path: Optional[str] = None,
                 auto_discover: bool = True):
        self.index_paths: List[str] = []
        self._index: List[Dict[str, Any]] = []

        if index_path is not None:
            self.index_paths = [index_path]
            self._load_index(index_path)
        elif auto_discover:
            self._auto_discover()
        else:
            # Default: single gpgpu index
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            default_path = os.path.join(project_root, "skills", "gpgpu", "skills_index.yaml")
            self.index_paths = [default_path]
            self._load_index(default_path)

    def _auto_discover(self) -> None:
        """Scan skills/ directory for all skills_index.yaml files."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        skills_dir = os.path.join(project_root, "skills")
        if not os.path.isdir(skills_dir):
            skills_dir = "skills"

        found = []
        for root, dirs, files in os.walk(skills_dir):
            if "skills_index.yaml" in files:
                found.append(os.path.join(root, "skills_index.yaml"))

        if not found:
            raise FileNotFoundError(f"No skills_index.yaml found under {skills_dir}")

        for path in found:
            self._load_index(path)
            self.index_paths.append(path)

    def _load_index(self, path: str) -> None:
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        skills = data.get("skills", []) if data else []
        self._index.extend(skills)

    def retrieve(self, query: RetrievalQuery, top_k: int = 6,
                 score_threshold: float = 0.10) -> List[ReferenceCard]:
        """Retrieve top-k relevant reference cards.

        Scores both top-level modules and their sub_modules.
        Sub_module matching allows fine-grained retrieval for specific
        implementation tasks (e.g., 'fetch', 'decode', 'alu').

        Default threshold lowered to 0.10 to allow sub_module matches
        where top-level behavior_tags don't overlap but sub_modules do.
        """
        candidates = []

        for skill in self._index:
            score = 0.0
            score += 0.25 * _overlap_score(query.behavior_tags, skill.get("behavior_tags", []))
            score += 0.20 * _overlap_score(query.interface_patterns, skill.get("interface_patterns", []))
            score += 0.20 * _overlap_score(query.control_patterns, skill.get("control_patterns", []))
            score += 0.15 * _overlap_score(query.datapath_patterns, skill.get("datapath_patterns", []))
            score += 0.10 * _keyword_score(query, skill)
            score += 0.10 * _maturity_score(skill)
            # Sub_module matching: find best matching sub_module
            score += 0.15 * _sub_module_score(query, skill)

            if score > score_threshold:
                candidates.append((score, skill))

        candidates.sort(key=lambda x: x[0], reverse=True)
        return [self._make_reference_card(score, skill, query)
                for score, skill in candidates[:top_k]]

    def _make_reference_card(self, score: float, skill: Dict[str, Any],
                             query: RetrievalQuery) -> ReferenceCard:
        """Build a reference card from a skill entry."""
        src = skill.get("source", {})
        name = src.get("class", skill.get("id", "").split(":")[-1])

        # Build why_relevant dynamically
        why = []
        matched_behaviors = set(query.behavior_tags) & set(skill.get("behavior_tags", []))
        matched_interfaces = set(query.interface_patterns) & set(skill.get("interface_patterns", []))
        matched_controls = set(query.control_patterns) & set(skill.get("control_patterns", []))
        if matched_behaviors:
            why.append(f"Behavior match: {', '.join(sorted(matched_behaviors))}")
        if matched_interfaces:
            why.append(f"Interface match: {', '.join(sorted(matched_interfaces))}")
        if matched_controls:
            why.append(f"Control match: {', '.join(sorted(matched_controls))}")

        # Extract useful ideas from summary
        useful = []
        summary = skill.get("summary", "")
        if summary:
            sentences = [s.strip() for s in summary.split(".") if s.strip()]
            useful = sentences[:3]

        # Reusable patterns
        reusable = skill.get("control_patterns", []) + skill.get("datapath_patterns", [])[:3]

        # Suggested adaptation
        adaptations = []
        for tag in query.behavior_tags:
            if tag in skill.get("behavior_tags", []):
                adaptations.append(f"Adapt {tag} to current module context")

        return ReferenceCard(
            skill_id=skill.get("id", ""),
            name=name,
            relevance=round(score, 3),
            source_file=src.get("file", ""),
            source_class=src.get("class", ""),
            kind=skill.get("kind", "module"),
            domain=skill.get("domain", ""),
            why_relevant=why,
            useful_ideas=useful,
            reusable_patterns=list(set(reusable)),
            suggested_adaptation=adaptations,
            caution=["Do not copy code directly; adapt to current ports and parameters."],
            summary=summary,
            behavior_tags=skill.get("behavior_tags", []),
            interface_patterns=skill.get("interface_patterns", []),
            control_patterns=skill.get("control_patterns", []),
            datapath_patterns=skill.get("datapath_patterns", []),
        )

    def retrieve_for_task(self, pe_type: str, task: Dict[str, Any],
                          behavior_req: Optional[Dict[str, Any]] = None,
                          top_k: int = 6) -> List[ReferenceCard]:
        """Convenience wrapper: build query from task dict and retrieve."""
        query = RetrievalQuery(
            target_module=task.get("name", ""),
            pe_type=pe_type,
            behavior_tags=task.get("behavior_tags", []),
            interface_patterns=task.get("interface_patterns", []),
            control_patterns=task.get("control_patterns", []),
            datapath_patterns=task.get("datapath_patterns", []),
            keywords=[pe_type, task.get("name", "")],
        )
        if behavior_req:
            query.behavior_tags.extend(behavior_req.get("behavior", []))
            query.interface_patterns.extend(behavior_req.get("interfaces", []))
            query.control_patterns.extend(behavior_req.get("control_patterns", []))
            query.datapath_patterns.extend(behavior_req.get("datapath_patterns", []))
        return self.retrieve(query, top_k=top_k)
