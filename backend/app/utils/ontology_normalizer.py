"""
온톨로지 이름과 참조를 Zep 제약에 맞게 정규화합니다.
"""

import re
from typing import Any, Dict, Iterable, List


RESERVED_ATTRIBUTE_NAMES = {
    "uuid",
    "name",
    "group_id",
    "name_embedding",
    "summary",
    "created_at",
}


def _split_words(value: str) -> List[str]:
    text = (value or "").strip()
    if not text:
        return []

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", text)
    text = re.sub(r"[^0-9A-Za-z]+", " ", text)
    return [word for word in text.split() if word]


def normalize_entity_type_name(name: str, fallback: str = "Entity") -> str:
    words = _split_words(name)
    if not words:
        return fallback

    normalized = "".join(word[:1].upper() + word[1:] for word in words)
    if normalized and normalized[0].isdigit():
        normalized = f"Type{normalized}"
    return normalized or fallback


def normalize_edge_type_name(name: str, fallback: str = "RELATED_TO") -> str:
    text = (name or "").strip()
    if not text:
        return fallback

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", text)
    text = re.sub(r"[^0-9A-Za-z]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_").upper()

    if not text:
        return fallback
    if text[0].isdigit():
        text = f"REL_{text}"
    return text


def normalize_attribute_name(name: str, fallback: str = "value") -> str:
    text = (name or "").strip()
    if not text:
        return fallback

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", text)
    text = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", text)
    text = re.sub(r"[^0-9A-Za-z]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_").lower()

    if not text:
        text = fallback
    if text[0].isdigit():
        text = f"field_{text}"
    if text in RESERVED_ATTRIBUTE_NAMES:
        text = f"entity_{text}"
    return text


def _merge_unique_list(
    existing_items: List[Any],
    new_items: Iterable[Any],
    key_fn,
) -> List[Any]:
    seen = {key_fn(item) for item in existing_items}
    for item in new_items:
        key = key_fn(item)
        if key in seen:
            continue
        existing_items.append(item)
        seen.add(key)
    return existing_items


def normalize_ontology(ontology: Dict[str, Any]) -> Dict[str, Any]:
    if not ontology:
        return {"entity_types": [], "edge_types": [], "analysis_summary": ""}

    normalized: Dict[str, Any] = {
        "entity_types": [],
        "edge_types": [],
        "analysis_summary": ontology.get("analysis_summary", ""),
    }

    entity_name_map: Dict[str, str] = {}
    normalized_entities: Dict[str, Dict[str, Any]] = {}

    for index, entity in enumerate(ontology.get("entity_types", []), start=1):
        source_name = entity.get("name", "")
        normalized_name = normalize_entity_type_name(source_name, fallback=f"EntityType{index}")
        entity_name_map[source_name] = normalized_name
        entity_name_map[normalized_name] = normalized_name

        normalized_attributes = []
        for attr_index, attr in enumerate(entity.get("attributes", []), start=1):
            attr_copy = dict(attr)
            attr_copy["name"] = normalize_attribute_name(
                attr.get("name", ""),
                fallback=f"field_{attr_index}",
            )
            normalized_attributes.append(attr_copy)

        normalized_entity = {
            **entity,
            "name": normalized_name,
            "attributes": [],
            "examples": list(entity.get("examples", [])),
        }
        _merge_unique_list(
            normalized_entity["attributes"],
            normalized_attributes,
            lambda item: item.get("name"),
        )

        existing_entity = normalized_entities.get(normalized_name)
        if existing_entity is None:
            normalized_entities[normalized_name] = normalized_entity
            normalized["entity_types"].append(normalized_entity)
            continue

        _merge_unique_list(
            existing_entity["attributes"],
            normalized_entity["attributes"],
            lambda item: item.get("name"),
        )
        _merge_unique_list(
            existing_entity["examples"],
            normalized_entity["examples"],
            lambda item: item,
        )
        if len(normalized_entity.get("description", "")) > len(existing_entity.get("description", "")):
            existing_entity["description"] = normalized_entity["description"]

    normalized_edges: Dict[str, Dict[str, Any]] = {}

    for index, edge in enumerate(ontology.get("edge_types", []), start=1):
        normalized_name = normalize_edge_type_name(edge.get("name", ""), fallback=f"RELATED_TO_{index}")

        normalized_attributes = []
        for attr_index, attr in enumerate(edge.get("attributes", []), start=1):
            attr_copy = dict(attr)
            attr_copy["name"] = normalize_attribute_name(
                attr.get("name", ""),
                fallback=f"field_{attr_index}",
            )
            normalized_attributes.append(attr_copy)

        normalized_source_targets = []
        for source_target in edge.get("source_targets", []):
            source = source_target.get("source", "Entity")
            target = source_target.get("target", "Entity")
            normalized_source_targets.append(
                {
                    "source": entity_name_map.get(source, normalize_entity_type_name(source)),
                    "target": entity_name_map.get(target, normalize_entity_type_name(target)),
                }
            )

        normalized_edge = {
            **edge,
            "name": normalized_name,
            "attributes": [],
            "source_targets": [],
        }
        _merge_unique_list(
            normalized_edge["attributes"],
            normalized_attributes,
            lambda item: item.get("name"),
        )
        _merge_unique_list(
            normalized_edge["source_targets"],
            normalized_source_targets,
            lambda item: (item.get("source"), item.get("target")),
        )

        existing_edge = normalized_edges.get(normalized_name)
        if existing_edge is None:
            normalized_edges[normalized_name] = normalized_edge
            normalized["edge_types"].append(normalized_edge)
            continue

        _merge_unique_list(
            existing_edge["attributes"],
            normalized_edge["attributes"],
            lambda item: item.get("name"),
        )
        _merge_unique_list(
            existing_edge["source_targets"],
            normalized_edge["source_targets"],
            lambda item: (item.get("source"), item.get("target")),
        )
        if len(normalized_edge.get("description", "")) > len(existing_edge.get("description", "")):
            existing_edge["description"] = normalized_edge["description"]

    return normalized
