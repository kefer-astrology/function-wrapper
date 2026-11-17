"""Built-in model catalog shared by Python resolution and parity tests."""

try:
    from module.models import (
        AspectDefinition,
        AstroModel,
        BodyDefinition,
        Element,
        EngineType,
        HouseSystem,
        ModelSettings,
        ObjectType,
        PositionMode,
        Sign,
        ZodiacType,
    )
except ImportError:
    from models import (
        AspectDefinition,
        AstroModel,
        BodyDefinition,
        Element,
        EngineType,
        HouseSystem,
        ModelSettings,
        ObjectType,
        PositionMode,
        Sign,
        ZodiacType,
    )


def builtin_model_settings() -> ModelSettings:
    return ModelSettings(
        default_house_system=HouseSystem.PLACIDUS,
        position_mode=PositionMode.APPARENT,
        default_aspects=[
            "conjunction",
            "sextile",
            "square",
            "trine",
            "quincunx",
            "opposition",
        ],
        default_bodies=[
            "sun",
            "moon",
            "mercury",
            "venus",
            "mars",
            "jupiter",
            "saturn",
            "uranus",
            "neptune",
            "pluto",
            "asc",
            "mc",
            "desc",
            "ic",
            "north_node",
            "south_node",
            "lilith",
            "chiron",
        ],
        standard_orb=1.0,
        degrees_in_circle=360.0,
        obliquity_j2000=23.4392911,
        coordinate_tolerance=0.0001,
    )


def _body(
    body_id: str,
    label: str,
    glyph: str,
    object_type: ObjectType,
    *,
    jpl: bool = True,
    swisseph: bool = True,
    requires_location: bool = False,
    requires_house_system: bool = False,
) -> BodyDefinition:
    return BodyDefinition(
        id=body_id,
        glyph=glyph,
        formula=body_id,
        element=None,
        avg_speed=0.0,
        max_orb=0.0,
        i18n={"en": label},
        object_type=object_type,
        computation_map={
            "swisseph": body_id if swisseph else None,
            "jpl": body_id if jpl else None,
        },
        requires_location=requires_location,
        requires_house_system=requires_house_system,
    )


# Canonical built-in aspects and aliases come from the pinned kefer-contracts
# (catalogs/aspects.json) via the generated module below; regenerate with
# `python -m devtools.sync_contracts`. Rust ids and default orbs are canonical
# (Phase 0 decision D4). Legacy ids are accepted wherever an aspect id is read;
# writers emit canonical ids.
try:
    from module._contract_catalog import ASPECT_ALIASES, ASPECT_CATALOG, ASPECT_CATALOG_VERSION
except ImportError:
    from _contract_catalog import ASPECT_ALIASES, ASPECT_CATALOG, ASPECT_CATALOG_VERSION


def canonical_aspect_id(aspect_id: str) -> str:
    """Canonical id for an aspect id; aliases match case-insensitively and any
    other id is returned unchanged (custom ids keep their spelling)."""
    return ASPECT_ALIASES.get(str(aspect_id).strip().lower(), aspect_id)


def canonical_aspect_ids(ids):
    """Canonicalize a list, dropping alias-created duplicates (first wins)."""
    out = []
    for aspect_id in ids or []:
        canonical = canonical_aspect_id(aspect_id)
        if canonical not in out:
            out.append(canonical)
    return out


def canonical_aspect_map(values):
    """Canonicalize map keys; an explicitly canonical key beats its alias."""
    out = {key: value for key, value in (values or {}).items() if canonical_aspect_id(key) == key}
    for key, value in (values or {}).items():
        canonical = canonical_aspect_id(key)
        if canonical != key:
            out.setdefault(canonical, value)
    return out


def _aspect(aspect_id: str, label: str, angle: float, orb: float) -> AspectDefinition:
    return AspectDefinition(
        id=aspect_id,
        glyph=label,
        angle=angle,
        default_orb=orb,
        i18n={"en": label},
    )


def _sign(name: str, glyph: str, abbreviation: str, element: Element) -> Sign:
    return Sign(
        name=name,
        glyph=glyph,
        abbreviation=abbreviation,
        element=element,
        i18n={"en": name},
    )


def builtin_standard_model(name: str = "standard") -> AstroModel:
    bodies = [
        _body("sun", "Sun", "☉", ObjectType.PLANET),
        _body("moon", "Moon", "☽", ObjectType.PLANET),
        _body("mercury", "Mercury", "☿", ObjectType.PLANET),
        _body("venus", "Venus", "♀", ObjectType.PLANET),
        _body("mars", "Mars", "♂", ObjectType.PLANET),
        _body("jupiter", "Jupiter", "♃", ObjectType.PLANET),
        _body("saturn", "Saturn", "♄", ObjectType.PLANET),
        _body("uranus", "Uranus", "♅", ObjectType.PLANET),
        _body("neptune", "Neptune", "♆", ObjectType.PLANET),
        _body("pluto", "Pluto", "♇", ObjectType.PLANET),
        _body("asc", "Ascendant", "Asc", ObjectType.ANGLE, requires_location=True),
        _body("mc", "Midheaven", "MC", ObjectType.ANGLE, requires_location=True),
        _body("desc", "Descendant", "Desc", ObjectType.ANGLE, requires_location=True),
        _body("ic", "Imum Coeli", "IC", ObjectType.ANGLE, requires_location=True),
        _body("north_node", "North Node", "☊", ObjectType.LUNAR_NODE),
        _body("south_node", "South Node", "☋", ObjectType.LUNAR_NODE),
        _body("true_north_node", "True North Node", "☊", ObjectType.LUNAR_NODE),
        _body("true_south_node", "True South Node", "☋", ObjectType.LUNAR_NODE),
        _body("lilith", "Lilith", "⚸", ObjectType.CALCULATED_POINT),
        _body("true_lilith", "True Lilith", "⚸", ObjectType.CALCULATED_POINT),
        _body("chiron", "Chiron", "⚷", ObjectType.ASTEROID),
        _body("ceres", "Ceres", "⚳", ObjectType.ASTEROID),
        _body("pallas", "Pallas", "⚴", ObjectType.ASTEROID),
        _body("juno", "Juno", "⚵", ObjectType.ASTEROID),
        _body("vesta", "Vesta", "⚶", ObjectType.ASTEROID),
        # Resolvable via the bundled/downloadable `codes_300ast_20100725.bsp` kernel
        # (see CODES_300AST_MAJOR_BODIES in Rust's infrastructure/ephemeris.rs), but
        # none of these has a dedicated astrological symbol in wide use — the glyph
        # is the circled digit matching the minor-planet number, a convention several
        # asteroid-ephemeris references already use for bodies without one. Swiss
        # Ephemeris support is left unclaimed: it would require asteroid `.se1` files
        # this project does not bundle.
        _body("astraea", "Astraea", "⑤", ObjectType.ASTEROID, swisseph=False),
        _body("hebe", "Hebe", "⑥", ObjectType.ASTEROID, swisseph=False),
        _body("iris", "Iris", "⑦", ObjectType.ASTEROID, swisseph=False),
        _body("flora", "Flora", "⑧", ObjectType.ASTEROID, swisseph=False),
        _body("metis", "Metis", "⑨", ObjectType.ASTEROID, swisseph=False),
        _body("hygiea", "Hygiea", "⑩", ObjectType.ASTEROID, swisseph=False),
        _body("parthenope", "Parthenope", "⑪", ObjectType.ASTEROID, swisseph=False),
        _body("victoria", "Victoria", "⑫", ObjectType.ASTEROID, swisseph=False),
        _body("egeria", "Egeria", "⑬", ObjectType.ASTEROID, swisseph=False),
        _body("irene", "Irene", "⑭", ObjectType.ASTEROID, swisseph=False),
        _body("eunomia", "Eunomia", "⑮", ObjectType.ASTEROID, swisseph=False),
        _body("psyche", "Psyche", "⑯", ObjectType.ASTEROID, swisseph=False),
        _body("thetis", "Thetis", "⑰", ObjectType.ASTEROID, swisseph=False),
        _body("melpomene", "Melpomene", "⑱", ObjectType.ASTEROID, swisseph=False),
        _body("fortuna", "Fortuna", "⑲", ObjectType.ASTEROID, swisseph=False),
        _body("massalia", "Massalia", "⑳", ObjectType.ASTEROID, swisseph=False),
    ]
    aspects = [_aspect(*row) for row in ASPECT_CATALOG]
    signs = [
        _sign("Aries", "Ar", "Ari", Element.FIRE),
        _sign("Taurus", "Ta", "Tau", Element.EARTH),
        _sign("Gemini", "Ge", "Gem", Element.AIR),
        _sign("Cancer", "Ca", "Can", Element.WATER),
        _sign("Leo", "Le", "Leo", Element.FIRE),
        _sign("Virgo", "Vi", "Vir", Element.EARTH),
        _sign("Libra", "Li", "Lib", Element.AIR),
        _sign("Scorpio", "Sc", "Sco", Element.WATER),
        _sign("Sagittarius", "Sg", "Sag", Element.FIRE),
        _sign("Capricorn", "Cp", "Cap", Element.EARTH),
        _sign("Aquarius", "Aq", "Aqu", Element.AIR),
        _sign("Pisces", "Pi", "Pis", Element.WATER),
    ]
    return AstroModel(
        name=name,
        body_definitions=bodies,
        aspect_definitions=aspects,
        signs=signs,
        settings=builtin_model_settings(),
        engine=EngineType.JPL,
        zodiac_type=ZodiacType.TROPICAL,
        ayanamsa=None,
    )
