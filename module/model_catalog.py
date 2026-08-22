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
        Sign,
        ZodiacType,
    )


def builtin_model_settings() -> ModelSettings:
    return ModelSettings(
        default_house_system=HouseSystem.PLACIDUS,
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
            "swisseph": body_id,
            "jpl": body_id if jpl else None,
        },
        requires_location=requires_location,
        requires_house_system=requires_house_system,
    )


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
    ]
    aspects = [
        _aspect("conjunction", "Conjunction", 0.0, 8.0),
        _aspect("sextile", "Sextile", 60.0, 6.0),
        _aspect("square", "Square", 90.0, 8.0),
        _aspect("trine", "Trine", 120.0, 8.0),
        _aspect("quincunx", "Quincunx", 150.0, 3.0),
        _aspect("opposition", "Opposition", 180.0, 8.0),
        _aspect("semisextile", "Semisextile", 30.0, 2.0),
        _aspect("decile", "Decile", 36.0, 1.0),
        _aspect("novile", "Novile", 40.0, 1.0),
        _aspect("semisquare", "Semisquare", 45.0, 2.0),
        _aspect("septile", "Septile", 360.0 / 7.0, 1.0),
        _aspect("quintile", "Quintile", 72.0, 2.0),
        _aspect("binovile", "Binovile", 80.0, 1.0),
        _aspect("tridecile", "Tridecile", 108.0, 1.0),
        _aspect("sesquiquadrate", "Sesquiquadrate", 135.0, 2.0),
        _aspect("biquintile", "Biquintile", 144.0, 2.0),
        _aspect("quadrinovile", "Quadrinovile", 160.0, 1.0),
    ]
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
