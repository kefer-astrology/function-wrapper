from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import math
import sys
import logging

# Modern logging setup
try:
    from module.logging_config import get_logger
except ImportError:
    from logging_config import get_logger

logger = get_logger(__name__)

# Standardized imports with fallback for direct execution
try:
    from module.models import (
        Aspect, AspectDefinition, AstroModel, BodyDefinition, CelestialBody, ChartMode, DateRange,
        EngineType, ChartConfig, ChartInstance, Location, ModelOverrides, ModelSettings, Sign,
        ObjectType, Workspace
    )
except ImportError:
    from models import (
        Aspect, AspectDefinition, AstroModel, BodyDefinition, CelestialBody, ChartMode, DateRange,
        EngineType, ChartConfig, ChartInstance, Location, ModelOverrides, ModelSettings, Sign,
        ObjectType, Workspace
    )

try:
    from module.utils import Actual, default_ephemeris_path, ensure_aware, prepare_horoscope, compute_vernal_equinox_offset, _safe_get_attr
except ImportError:
    from utils import Actual, default_ephemeris_path, ensure_aware, prepare_horoscope, compute_vernal_equinox_offset, _safe_get_attr

try:
    from module.z_visual import build_radix_figure
except ImportError:
    from z_visual import build_radix_figure

from kerykeion import AstrologicalSubject, KerykeionChartSVG
# KerykeionPointModel and Report may have different import paths in different versions
try:
    from kerykeion import KerykeionPointModel
except ImportError:
    try:
        from kerykeion.kr_types.kr_models import KerykeionPointModel
    except ImportError:
        # KerykeionPointModel not available in this version
        KerykeionPointModel = None

# Report may be in kerykeion.report in some versions
try:
    from kerykeion import Report
except ImportError:
    try:
        from kerykeion.report import Report
    except ImportError:
        # Report not available in this version of kerykeion
        Report = None
from pandas import DataFrame

try:
    from skyfield.api import load, load_file, Topos
    JPL = True
except ImportError:
    JPL = False
    logger.warning("NASA JPL Ephemeris deactivated")

# Module-level fallback constants (used when model is not available)
# These match ModelSettings defaults and can be overridden by model settings
DEGREES_IN_CIRCLE = 360.0  # Full circle in degrees
OBLIQUITY_J2000_DEGREES = 23.4392911  # J2000.0 obliquity of the ecliptic in degrees
COORDINATE_TOLERANCE = 0.0001  # Coordinate comparison tolerance


# ─────────────────────
# 🗺️ COMPUTATION MAPPING SYSTEM
# ─────────────────────

def _get_kerykeion_object_mapping() -> Dict[str, str]:
    """Map object IDs to kerykeion AstrologicalSubject attribute names.
    
    Returns a dict mapping object_id -> attribute_name for kerykeion extraction.
    """
    return {
        # Planets (standard)
        "sun": "sun",
        "moon": "moon",
        "mercury": "mercury",
        "venus": "venus",
        "mars": "mars",
        "jupiter": "jupiter",
        "saturn": "saturn",
        "uranus": "uranus",
        "neptune": "neptune",
        "pluto": "pluto",
        # Angles
        "asc": "asc",
        "ascendant": "asc",
        "desc": "desc",
        "descendant": "desc",
        "mc": "mc",
        "midheaven": "mc",
        "ic": "ic",
        "imum_coeli": "ic",
        # Lunar nodes
        "north_node": "north_node",
        "south_node": "south_node",
        "true_north_node": "true_north_node",
        "true_south_node": "true_south_node",
        # Calculated points
        "lilith": "lilith",
        "black_moon_lilith": "lilith",
        "chiron": "chiron",
        "ceres": "ceres",
        "pallas": "pallas",
        "juno": "juno",
        "vesta": "vesta",
        # Houses (will be handled separately via houses_list)
        "house_1": "house_1",
        "house_2": "house_2",
        "house_3": "house_3",
        "house_4": "house_4",
        "house_5": "house_5",
        "house_6": "house_6",
        "house_7": "house_7",
        "house_8": "house_8",
        "house_9": "house_9",
        "house_10": "house_10",
        "house_11": "house_11",
        "house_12": "house_12",
    }


def _extract_kerykeion_observable_objects(subj: AstrologicalSubject, requested_objects: Optional[List[str]] = None, model: Optional[AstroModel] = None) -> Dict[str, float]:
    """Extract all observable objects from a kerykeion AstrologicalSubject.
    
    Includes planets, angles, houses, lunar nodes, and calculated points.
    Returns a dict mapping object_id -> ecliptic_longitude (degrees).
    """
    positions: Dict[str, float] = {}
    mapping = _get_kerykeion_object_mapping()
    lon_keys = ("ecliptic_longitude", "longitude", "lon", "degree", "deg")
    
    # Get degrees_in_circle from model settings or use default
    if model and hasattr(model, 'settings') and hasattr(model.settings, 'degrees_in_circle'):
        degrees_in_circle = model.settings.degrees_in_circle
    else:
        degrees_in_circle = 360.0  # Default fallback
    
    # First, try the most reliable method: planets_list and planets_degrees_ut (older Kerykeion versions)
    # This is the primary data source in older Kerykeion versions
    if hasattr(subj, 'planets_list') and hasattr(subj, 'planets_degrees_ut'):
        try:
            planets_list = subj.planets_list
            planets_degrees = subj.planets_degrees_ut
            if isinstance(planets_list, list) and isinstance(planets_degrees, list) and len(planets_list) == len(planets_degrees):
                for i, planet_info in enumerate(planets_list):
                    if i < len(planets_degrees):
                        if isinstance(planet_info, dict):
                            planet_name = planet_info.get('name', '').strip().lower()
                        else:
                            planet_name = str(planet_info).strip().lower() if planet_info else ''
                        
                        if planet_name:
                            obj_id = mapping.get(planet_name, planet_name)
                            if requested_objects and obj_id not in requested_objects and planet_name not in requested_objects:
                                continue
                            try:
                                # Normalize to [0, 360) range (same as JPL)
                                lon_float = float(planets_degrees[i])
                                normalized_lon = lon_float % degrees_in_circle
                                if normalized_lon < 0:
                                    normalized_lon += degrees_in_circle
                                positions[obj_id] = normalized_lon
                            except (ValueError, TypeError, IndexError) as e:
                                logger.debug("Failed to extract position for %s from planets_degrees_ut: %s", planet_name, e)
                                continue
                if positions:
                    logger.debug("Successfully extracted %d positions from planets_list/planets_degrees_ut", len(positions))
        except Exception as e:
            logger.debug("Failed to extract from planets_list/planets_degrees_ut: %s", e, exc_info=True)
    
    # If planets_list method didn't work, try direct planet attributes (newer Kerykeion versions)
    # Newer versions store planets as direct attributes (subj.sun, subj.moon, etc.)
    # Also try if they're simple numeric values (float) rather than objects
    if not positions:
        logger.debug("planets_list not available, trying direct planet attributes (newer Kerykeion API)")
        # Try direct numeric attributes first (simplest case)
        planet_attrs = ['sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto']
        for planet_name in planet_attrs:
            if hasattr(subj, planet_name):
                try:
                    planet_val = getattr(subj, planet_name)
                    logger.debug("  Checking %s: type=%s, value=%s", planet_name, type(planet_val).__name__, planet_val)
                    # If it's a direct numeric value (float/int), use it
                    if isinstance(planet_val, (int, float)):
                        obj_id = mapping.get(planet_name, planet_name)
                        if requested_objects and obj_id not in requested_objects and planet_name not in requested_objects:
                            logger.debug("  Skipping %s (not in requested_objects)", planet_name)
                            continue
                        normalized_lon = float(planet_val) % degrees_in_circle
                        if normalized_lon < 0:
                            normalized_lon += degrees_in_circle
                        positions[obj_id] = normalized_lon
                        logger.debug("  ✓ Extracted %s as direct numeric value: %s", planet_name, normalized_lon)
                    else:
                        logger.debug("  %s is not numeric (type: %s), will try as object later", planet_name, type(planet_val).__name__)
                except (ValueError, TypeError, AttributeError) as e:
                    logger.debug("  Failed to extract %s as direct numeric: %s", planet_name, e, exc_info=True)
        
        # Also try angles as direct numeric values
        angle_attrs = {
            'ascendant': 'asc',
            'asc': 'asc',
            'descendant': 'desc',
            'desc': 'desc',
            'midheaven': 'mc',
            'mc': 'mc',
            'imum_coeli': 'ic',
            'ic': 'ic',
        }
        for attr_name, obj_id in angle_attrs.items():
            if hasattr(subj, attr_name):
                try:
                    angle_val = getattr(subj, attr_name)
                    logger.debug("  Checking angle %s: type=%s, value=%s", attr_name, type(angle_val).__name__, angle_val)
                    if isinstance(angle_val, (int, float)):
                        if requested_objects and obj_id not in requested_objects and attr_name not in requested_objects:
                            logger.debug("  Skipping %s (not in requested_objects)", attr_name)
                            continue
                        normalized_lon = float(angle_val) % degrees_in_circle
                        if normalized_lon < 0:
                            normalized_lon += degrees_in_circle
                        positions[obj_id] = normalized_lon
                        logger.debug("  ✓ Extracted %s as direct numeric value: %s", attr_name, normalized_lon)
                    else:
                        logger.debug("  %s is not numeric (type: %s), will try as object later", attr_name, type(angle_val).__name__)
                except (ValueError, TypeError, AttributeError) as e:
                    logger.debug("  Failed to extract %s as direct numeric: %s", attr_name, e, exc_info=True)
        
        # Try houses (first_house, second_house, etc. or eighth_house suggests they might be named differently)
        house_attrs = [f'first_house', f'second_house', f'third_house', f'fourth_house', 
                      f'fifth_house', f'sixth_house', f'seventh_house', f'eighth_house',
                      f'ninth_house', f'tenth_house', f'eleventh_house', f'twelfth_house']
        for i, house_attr in enumerate(house_attrs, 1):
            if hasattr(subj, house_attr):
                try:
                    house_val = getattr(subj, house_attr)
                    logger.debug("  Checking house %s: type=%s, value=%s", house_attr, type(house_val).__name__, house_val)
                    if isinstance(house_val, (int, float)):
                        house_id = f"house_{i}"
                        if requested_objects and house_id not in requested_objects:
                            logger.debug("  Skipping %s (not in requested_objects)", house_attr)
                            continue
                        normalized_lon = float(house_val) % degrees_in_circle
                        if normalized_lon < 0:
                            normalized_lon += degrees_in_circle
                        positions[house_id] = normalized_lon
                        logger.debug("  ✓ Extracted %s as direct numeric value: %s", house_attr, normalized_lon)
                    else:
                        logger.debug("  %s is not numeric (type: %s)", house_attr, type(house_val).__name__)
                except (ValueError, TypeError, AttributeError) as e:
                    logger.debug("  Failed to extract %s as direct numeric: %s", house_attr, e, exc_info=True)
        
        # Also try chiron and other calculated points
        calc_points = ['chiron', 'lilith', 'north_node', 'south_node', 'true_north_node', 'true_south_node']
        for point_name in calc_points:
            if hasattr(subj, point_name):
                try:
                    point_val = getattr(subj, point_name)
                    logger.debug("  Checking calculated point %s: type=%s, value=%s", point_name, type(point_val).__name__, point_val)
                    if isinstance(point_val, (int, float)):
                        obj_id = mapping.get(point_name, point_name)
                        if requested_objects and obj_id not in requested_objects and point_name not in requested_objects:
                            logger.debug("  Skipping %s (not in requested_objects)", point_name)
                            continue
                        normalized_lon = float(point_val) % degrees_in_circle
                        if normalized_lon < 0:
                            normalized_lon += degrees_in_circle
                        positions[obj_id] = normalized_lon
                        logger.debug("  ✓ Extracted %s as direct numeric value: %s", point_name, normalized_lon)
                    else:
                        logger.debug("  %s is not numeric (type: %s), will try as object later", point_name, type(point_val).__name__)
                except (ValueError, TypeError, AttributeError) as e:
                    logger.debug("  Failed to extract %s as direct numeric: %s", point_name, e, exc_info=True)
        
        if positions:
            logger.debug("Successfully extracted %d positions from direct numeric attributes", len(positions))
        else:
            logger.debug("No positions extracted from direct numeric attributes - all attributes may be objects, not numeric")
    
    # Extract from KerykeionPointModel attributes (if available)
    # This handles planets/angles/houses that are objects, not direct numeric values
    if KerykeionPointModel is not None:
        logger.debug("Checking for KerykeionPointModel objects...")
        for attr_name in dir(subj):
            if attr_name.startswith('_'):
                continue
            try:
                attr = getattr(subj, attr_name)
                if isinstance(attr, KerykeionPointModel):
                    # Try to get the object name/id
                    obj_name = (getattr(attr, "name", None) or attr_name or "").strip().lower()
                    # Normalize name using mapping
                    obj_id = mapping.get(obj_name, obj_name)
                    
                    # Check if this object is requested
                    if requested_objects and obj_id not in requested_objects and obj_name not in requested_objects:
                        continue
                    
                    # Extract longitude - prioritize abs_pos (absolute position 0-360)
                    lon_val = None
                    
                    # FIRST: Try abs_pos directly (most reliable for newer Kerykeion)
                    if hasattr(attr, 'abs_pos'):
                        try:
                            lon_val = getattr(attr, 'abs_pos')
                            logger.debug("  ✓ Extracted %s.abs_pos = %s", attr_name, lon_val)
                        except (AttributeError, TypeError):
                            pass
                    
                    # SECOND: Try abs_pos from __dict__ (in case it's not a direct attribute)
                    if lon_val is None and hasattr(attr, '__dict__'):
                        if 'abs_pos' in attr.__dict__:
                            try:
                                lon_val = attr.__dict__['abs_pos']
                                logger.debug("  ✓ Extracted %s.__dict__['abs_pos'] = %s", attr_name, lon_val)
                            except (KeyError, TypeError):
                                pass
                    
                    # THIRD: Try standard longitude keys
                    if lon_val is None:
                        for k in lon_keys:
                            if hasattr(attr, k):
                                try:
                                    lon_val = getattr(attr, k)
                                    logger.debug("  ✓ Extracted %s.%s = %s", attr_name, k, lon_val)
                                    break
                                except (AttributeError, TypeError):
                                    continue
                    
                    # FOURTH: Try position + sign_num calculation
                    if lon_val is None:
                        if hasattr(attr, '__dict__'):
                            if 'position' in attr.__dict__ and 'sign_num' in attr.__dict__:
                                try:
                                    sign_num = attr.__dict__.get('sign_num', 0)
                                    pos_val = attr.__dict__['position']
                                    # position is 0-30 within sign, sign_num is 0-11 (Aries=0, Taurus=1, etc.)
                                    # Absolute longitude = sign_num * 30 + position
                                    lon_val = float(sign_num) * 30.0 + float(pos_val)
                                    logger.debug("  ✓ Calculated %s from sign_num=%s + position=%s = %s", attr_name, sign_num, pos_val, lon_val)
                                except (ValueError, TypeError, KeyError):
                                    pass
                            elif 'position' in attr.__dict__:
                                try:
                                    lon_val = attr.__dict__['position']
                                    logger.debug("  ✓ Extracted %s.__dict__['position'] = %s", attr_name, lon_val)
                                except (KeyError, TypeError):
                                    pass
                    
                    # FIFTH: Try position as direct attribute
                    if lon_val is None and hasattr(attr, 'position'):
                        try:
                            pos_val = getattr(attr, 'position')
                            if hasattr(attr, 'sign_num'):
                                try:
                                    sign_num = getattr(attr, 'sign_num', 0)
                                    lon_val = float(sign_num) * 30.0 + float(pos_val)
                                    logger.debug("  ✓ Calculated %s from sign_num=%s + position=%s = %s", attr_name, sign_num, pos_val, lon_val)
                                except (ValueError, TypeError):
                                    lon_val = pos_val
                            else:
                                lon_val = pos_val
                                logger.debug("  ✓ Extracted %s.position = %s", attr_name, lon_val)
                        except (AttributeError, TypeError):
                            pass
                    
                    if lon_val is not None:
                        try:
                            # Normalize to [0, 360) range (same as JPL)
                            lon_float = float(lon_val)
                            normalized_lon = lon_float % degrees_in_circle
                            if normalized_lon < 0:
                                normalized_lon += degrees_in_circle
                            positions[obj_id] = normalized_lon
                            logger.debug("  ✓ Added %s -> %s (normalized)", obj_id, normalized_lon)
                        except (ValueError, TypeError) as e:
                            logger.debug("  ✗ Failed to normalize %s: %s", attr_name, e)
                            continue
                    else:
                        logger.debug("  ✗ Could not extract longitude from %s (tried abs_pos, position, sign_num calculation)", attr_name)
            except Exception as e:
                logger.debug("  ✗ Exception extracting from %s: %s", attr_name, e, exc_info=True)
                continue
    
    # Direct planet attribute extraction (for newer kerykeion versions)
    # Try accessing planets directly as attributes (sun, moon, mercury, etc.)
    planet_attrs = ['sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto']
    for planet_name in planet_attrs:
        if hasattr(subj, planet_name):
            try:
                planet_obj = getattr(subj, planet_name)
                if planet_obj is None:
                    continue
                # Try to extract longitude from the planet object
                lon_val = None
                # FIRST: Try accessing via __dict__ for position/abs_pos (newer kerykeion versions)
                # This must be checked first because position/abs_pos are in __dict__ but not as direct attributes
                if hasattr(planet_obj, '__dict__'):
                    # Prefer abs_pos over position (abs_pos is absolute longitude, position might be relative to sign)
                    if 'abs_pos' in planet_obj.__dict__:
                        lon_val = planet_obj.__dict__['abs_pos']
                    elif 'position' in planet_obj.__dict__:
                        pos_val = planet_obj.__dict__['position']
                        # If position is relative to sign, calculate absolute from sign_num + position
                        if 'sign_num' in planet_obj.__dict__:
                            sign_num = planet_obj.__dict__.get('sign_num', 0)
                            try:
                                # position is 0-30 within sign, sign_num is 0-11 (Aries=0, Taurus=1, etc.)
                                # Absolute longitude = sign_num * 30 + position
                                lon_val = float(sign_num) * 30.0 + float(pos_val)
                            except (ValueError, TypeError):
                                # If calculation fails, try using position as-is
                                lon_val = pos_val
                        else:
                            lon_val = pos_val
                
                # SECOND: Try standard attribute access (hasattr/getattr)
                if lon_val is None:
                    for k in lon_keys:
                        if hasattr(planet_obj, k):
                            lon_val = getattr(planet_obj, k)
                            break
                
                # THIRD: Try accessing as a dict if it's dict-like
                if lon_val is None and isinstance(planet_obj, dict):
                    for k in lon_keys:
                        if k in planet_obj:
                            lon_val = planet_obj[k]
                            break
                
                # FOURTH: Try __dict__ for standard longitude keys as fallback
                if lon_val is None and hasattr(planet_obj, '__dict__'):
                    for k in lon_keys:
                        if k in planet_obj.__dict__:
                            lon_val = planet_obj.__dict__[k]
                            break
                
                if lon_val is not None:
                    try:
                        # Convert to float and normalize to [0, 360) range (same as JPL)
                        lon_float = float(lon_val)
                        # Normalize to [0, 360) range (same normalization as JPL)
                        normalized_lon = lon_float % DEGREES_IN_CIRCLE
                        if normalized_lon < 0:
                            normalized_lon += DEGREES_IN_CIRCLE
                        positions[planet_name] = normalized_lon
                    except (ValueError, TypeError) as e:
                        # If position is a dict or complex object, try to extract numeric value
                        if isinstance(lon_val, dict):
                            # Try common keys that might contain the degree value
                            for key in ['degree', 'deg', 'longitude', 'lon', 'value', 'abs']:
                                if key in lon_val:
                                    try:
                                        normalized_lon = float(lon_val[key]) % degrees_in_circle
                                        if normalized_lon < 0:
                                            normalized_lon += degrees_in_circle
                                        positions[planet_name] = normalized_lon
                                        break
                                    except (ValueError, TypeError, KeyError):
                                        continue
                        continue
            except Exception as e:
                continue
    
    # Extract houses from houses_list if available
    if hasattr(subj, 'houses_list') and isinstance(subj.houses_list, list):
        for i, house_info in enumerate(subj.houses_list, 1):
            house_id = f"house_{i}"
            if requested_objects and house_id not in requested_objects:
                continue
            try:
                if isinstance(house_info, dict):
                    # Try different possible keys
                    degree = (house_info.get('longitude') or 
                             house_info.get('lon') or 
                             house_info.get('degree') or
                             house_info.get('cusp'))
                    if degree is not None:
                        # Normalize to [0, 360) range (same as JPL)
                        lon_float = float(degree)
                        normalized_lon = lon_float % degrees_in_circle
                        if normalized_lon < 0:
                            normalized_lon += degrees_in_circle
                        positions[house_id] = normalized_lon
                elif hasattr(house_info, 'longitude'):
                    # Normalize to [0, 360) range (same as JPL)
                    lon_float = float(house_info.longitude)
                    normalized_lon = lon_float % degrees_in_circle
                    if normalized_lon < 0:
                        normalized_lon += degrees_in_circle
                    positions[house_id] = normalized_lon
            except (ValueError, TypeError, AttributeError):
                continue
    
    # Note: planets_list extraction is now done at the start of the function
    # This section is kept for backward compatibility but should not be reached if the above worked
    
    return positions


# ─────────────────────
# 🪐 POSITION CALCULATIONS (Skyfield-based for JPL)
# ─────────────────────

def _compute_planet_ecliptic_longitude(body, eph, observer, t, vernal_equinox_offset: float) -> Optional[float]:
    """Compute ecliptic longitude for a planet from RA/Dec.
    
    Args:
        body: Skyfield body object
        eph: Skyfield ephemeris
        observer: Skyfield Topos observer
        t: Skyfield time object
        vernal_equinox_offset: Offset to adjust for vernal equinox
        
    Returns:
        Ecliptic longitude in degrees [0, 360), or None on error
    """
    try:
        astrometric = (eph["earth"] + observer).at(t).observe(body).apparent()
        ra, dec, _ = astrometric.radec()
        
        # Compute ecliptic longitude from RA/Dec using J2000.0 obliquity
        ra_deg = ra.hours * 15.0  # Convert hours to degrees
        dec_deg = dec.degrees
        ra_rad = math.radians(ra_deg)
        dec_rad = math.radians(dec_deg)
        obliquity_j2000_deg = OBLIQUITY_J2000_DEGREES
        obliquity_j2000 = math.radians(obliquity_j2000_deg)  # J2000.0 obliquity
        
        # Formula: tan(ecl_lon) = (sin(RA) * cos(obl) + tan(Dec) * sin(obl)) / cos(RA)
        sin_ra = math.sin(ra_rad)
        cos_ra = math.cos(ra_rad)
        tan_dec = math.tan(dec_rad)
        sin_obl = math.sin(obliquity_j2000)
        cos_obl = math.cos(obliquity_j2000)
        
        ecl_lon_rad = math.atan2(sin_ra * cos_obl + tan_dec * sin_obl, cos_ra)
        lon_deg = math.degrees(ecl_lon_rad) % DEGREES_IN_CIRCLE
        if lon_deg < 0:
            lon_deg += DEGREES_IN_CIRCLE
        
        # Adjust for vernal equinox: subtract the offset so vernal equinox = 0°
        lon_deg_tropical = (lon_deg - vernal_equinox_offset) % DEGREES_IN_CIRCLE
        if lon_deg_tropical < 0:
            lon_deg_tropical += DEGREES_IN_CIRCLE
        
        return lon_deg_tropical
    except (KeyError, ValueError, AttributeError) as e:
        logger.warning("Could not compute planet position: %s", e)
        return None


def _compute_planet_extended_position(body, eph, observer, t, vernal_equinox_offset: float, 
                                      include_physical: bool = False, 
                                      include_topocentric: bool = False) -> Optional[Dict[str, float]]:
    """Compute extended position data for a planet using Skyfield.
    
    Args:
        body: Skyfield body object
        eph: Skyfield ephemeris
        observer: Skyfield Topos observer
        t: Skyfield time object
        vernal_equinox_offset: Offset to adjust for vernal equinox
        include_physical: If True, include magnitude/phase/elongation
        include_topocentric: If True, include altitude/azimuth
        
    Returns:
        Dictionary with position data, or None on error. Keys:
        - longitude: float (degrees, always present)
        - latitude: float (degrees, if available)
        - distance: float (AU, always present for JPL)
        - declination: float (degrees, always present for JPL)
        - right_ascension: float (degrees, always present for JPL)
        - altitude: float (degrees, if include_topocentric)
        - azimuth: float (degrees, if include_topocentric)
        - apparent_magnitude: float (if include_physical)
        - phase_angle: float (degrees, if include_physical)
        - elongation: float (degrees, if include_physical)
        - light_time: float (seconds, if include_physical)
        - speed: float (degrees/day, if available)
        - retrograde: bool (if available)
    """
    try:
        astrometric = (eph["earth"] + observer).at(t).observe(body).apparent()
        ra, dec, distance = astrometric.radec()
        
        # Always compute basic equatorial coordinates
        ra_deg = ra.hours * 15.0  # Convert hours to degrees
        dec_deg = dec.degrees
        distance_au = distance.au  # Distance in AU
        
        # Compute ecliptic longitude from RA/Dec
        ra_rad = math.radians(ra_deg)
        dec_rad = math.radians(dec_deg)
        obliquity_j2000_deg = OBLIQUITY_J2000_DEGREES
        obliquity_j2000 = math.radians(obliquity_j2000_deg)  # J2000.0 obliquity
        
        sin_ra = math.sin(ra_rad)
        cos_ra = math.cos(ra_rad)
        tan_dec = math.tan(dec_rad)
        sin_obl = math.sin(obliquity_j2000)
        cos_obl = math.cos(obliquity_j2000)
        
        ecl_lon_rad = math.atan2(sin_ra * cos_obl + tan_dec * sin_obl, cos_ra)
        lon_deg = math.degrees(ecl_lon_rad) % DEGREES_IN_CIRCLE
        if lon_deg < 0:
            lon_deg += DEGREES_IN_CIRCLE
        
        # Adjust for vernal equinox
        lon_deg_tropical = (lon_deg - vernal_equinox_offset) % DEGREES_IN_CIRCLE
        if lon_deg_tropical < 0:
            lon_deg_tropical += DEGREES_IN_CIRCLE
        
        # Build result dictionary
        result = {
            'longitude': float(lon_deg_tropical),
            'distance': float(distance_au),
            'declination': float(dec_deg),
            'right_ascension': float(ra_deg),
        }
        
        # Compute ecliptic latitude (optional, may not always be needed)
        # For now, set to 0.0 as approximation (full calculation would require more complex math)
        result['latitude'] = 0.0
        
        # Topocentric coordinates (altitude/azimuth)
        if include_topocentric:
            try:
                alt, az, _ = observer.at(t).observe(body).apparent().altaz()
                result['altitude'] = float(alt.degrees)
                result['azimuth'] = float(az.degrees)
            except Exception:
                pass  # Topocentric may not be available for all bodies
        
        # Physical properties
        if include_physical:
            try:
                # Light time is available from astrometric
                result['light_time'] = float(astrometric.light_time * 86400.0)  # Convert days to seconds
                
                # For planets, compute phase angle and elongation
                # Phase angle: angle between Sun, planet, and Earth
                # Elongation: angular distance from Sun
                try:
                    sun = eph["sun"]
                    sun_astrometric = (eph["earth"] + observer).at(t).observe(sun).apparent()
                    # Compute elongation (simplified - full calculation would use spherical trigonometry)
                    # For now, approximate using ecliptic longitude difference
                    sun_ra, sun_dec, _ = sun_astrometric.radec()
                    sun_ra_deg = sun_ra.hours * 15.0
                    # Elongation approximation (full calculation would be more complex)
                    elongation_approx = abs(ra_deg - sun_ra_deg)
                    if elongation_approx > 180.0:
                        elongation_approx = DEGREES_IN_CIRCLE - elongation_approx
                    result['elongation'] = float(elongation_approx)
                    
                    # Phase angle approximation (simplified)
                    # Full calculation would use distance to Sun and distance to planet
                    result['phase_angle'] = float(elongation_approx)  # Approximation
                except Exception:
                    pass
                
                # Apparent magnitude (not directly available from Skyfield for all bodies)
                # Would need additional computation or lookup tables
                # For now, skip this as it requires more complex calculations
            except Exception:
                pass
        
        # Speed and retrograde (would require computing position at two time points)
        # For now, set defaults - full implementation would compute speed from two positions
        result['speed'] = 0.0  # Placeholder - would need to compute from two time points
        result['retrograde'] = False  # Placeholder - would need to compute from speed
        
        return result
    except (KeyError, ValueError, AttributeError) as e:
        logger.warning("Could not compute extended planet position: %s", e)
        return None


def _compute_single_planet_position(planet: str, eph, observer, t, is_de421: bool, 
                                     vernal_equinox_offset: float) -> Optional[float]:
    """Compute position for a single planet.
    
    Args:
        planet: Planet name (e.g., "jupiter")
        eph: Skyfield ephemeris
        observer: Skyfield Topos observer
        t: Skyfield time object
        is_de421: Whether using de421 ephemeris (requires barycenters for outer planets)
        vernal_equinox_offset: Offset to adjust for vernal equinox
        
    Returns:
        Ecliptic longitude in degrees [0, 360), or None on error
    """
    outer_planets = ["jupiter", "saturn", "uranus", "neptune", "pluto"]
    
    # For de421, always try barycenter first for outer planets to avoid Skyfield errors
    if is_de421 and planet in outer_planets:
        body_name = f"{planet} barycenter"
        try:
            body = eph[body_name]
            return _compute_planet_ecliptic_longitude(body, eph, observer, t, vernal_equinox_offset)
        except (KeyError, ValueError, AttributeError) as e:
            logger.warning("Could not compute %s barycenter position: %s", planet, e)
            return None
    
    # For non-de421 or inner planets, try direct name first
    try:
        body = eph[planet]
        return _compute_planet_ecliptic_longitude(body, eph, observer, t, vernal_equinox_offset)
    except KeyError:
        # If direct access fails, try barycenter for outer planets (for other ephemeris files)
        if planet in outer_planets:
            try:
                body_name = f"{planet} barycenter"
                body = eph[body_name]
                return _compute_planet_ecliptic_longitude(body, eph, observer, t, vernal_equinox_offset)
            except (KeyError, ValueError, AttributeError) as e:
                logger.warning("Could not compute %s position: %s", planet, e)
                return None
        return None


def compute_jpl_positions(name: str, dt_str: str, loc_str: str, ephemeris_path: Optional[str] = None,
                          requested_objects: Optional[List[str]] = None,
                          include_physical: bool = False,
                          include_topocentric: bool = False,
                          extended: bool = False) -> Union[Dict[str, float], Dict[str, Dict[str, float]]]:
    """Compute planetary positions using Skyfield JPL ephemerides.

    Parameters:
    - name: subject name (human-readable; not used in computation)
    - dt_str: datetime string (parsed by utils.Actual)
    - loc_str: location string (parsed by utils.Actual)
    - ephemeris_path: optional path to a local BSP file; falls back to default
    - requested_objects: optional list of object IDs to compute
    - include_physical: if True, include magnitude/phase/elongation (extended mode only)
    - include_topocentric: if True, include altitude/azimuth (extended mode only)
    - extended: if True, return extended format with distance/declination/RA

    Returns:
    - If extended=False: mapping planet -> ecliptic longitude in degrees [0, 360)
    - If extended=True: mapping planet -> dict with extended properties
    """
    if JPL:
        ts = load.timescale()
        time = Actual(dt_str, t="date")
        place = Actual(loc_str, t="loc")

        # Ensure timezone-aware datetime using centralized utils
        dt_aware = ensure_aware(time.value, getattr(place, 'tz', None))
        t = ts.from_datetime(dt_aware)
        
        eph_file = ephemeris_path or default_ephemeris_path()
        # Use load_file for explicit local path support
        eph = load_file(eph_file)
        observer = Topos(latitude_degrees=place.value.latitude, longitude_degrees=place.value.longitude)
        
        # Check if we're using de421 (which requires barycenters for outer planets: Jupiter, Saturn, Uranus, Neptune, Pluto)
        is_de421 = eph_file and "de421" in Path(eph_file).name.lower()
        
        # Determine which planets to compute
        jpl_supported = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]
        if requested_objects:
            # Filter to only requested objects that JPL can compute
            planets = [p for p in jpl_supported if p in requested_objects]
        else:
            planets = jpl_supported
        
        positions = {}
        
        # For tropical astrology, we need to adjust for the vernal equinox of date
        year = dt_aware.year
        vernal_equinox_offset = compute_vernal_equinox_offset(year, eph, observer, ts)

        for planet in planets:
            if extended:
                # Get body for extended computation
                body = None
                outer_planets = ["jupiter", "saturn", "uranus", "neptune", "pluto"]
                if is_de421 and planet in outer_planets:
                    try:
                        body = eph[f"{planet} barycenter"]
                    except KeyError:
                        pass
                if body is None:
                    try:
                        body = eph[planet]
                    except KeyError:
                        if planet in outer_planets:
                            try:
                                body = eph[f"{planet} barycenter"]
                            except KeyError:
                                pass
                
                if body is not None:
                    extended_pos = _compute_planet_extended_position(
                        body, eph, observer, t, vernal_equinox_offset,
                        include_physical=include_physical,
                        include_topocentric=include_topocentric
                    )
                    if extended_pos is not None:
                        positions[planet] = extended_pos
            else:
                # Legacy mode: return only longitude
                lon_deg_tropical = _compute_single_planet_position(planet, eph, observer, t, is_de421, vernal_equinox_offset)
                if lon_deg_tropical is not None:
                    positions[planet] = lon_deg_tropical

        return positions
    else:
        # Return empty dict instead of string to maintain consistent return type
        return {}


# ─────────────────────
# 🪐 POSITION CALCULATIONS (Kerykeion-based)
# ─────────────────────
# TO-DO: decide between class and a method

class Subject:
    """Lightweight wrapper around Kerykeion's AstrologicalSubject builder.

    Usage:
    - Call at_place() then at_time() to prepare `self.computed`.
    - Use data() to extract names, degrees, and labels for plotting.
    """
    def __init__(self, s_name: str, s_type: str = "Tropic") -> None:
        self.computed = None
        self.name = s_name
        self.place = None
        self.time = None
        self.type = s_type

    def at_place(self, location: object) -> None:
        """Set place from a free-text location or coordinates string."""
        self.place = Actual(location, t="loc")

    def at_time(self, time: str) -> None:
        """Set event time from a free-text datetime string and build computed subject."""
        self.time = Actual(time, t="date")
        self.computed = AstrologicalSubject(
            self.name,
            self.time.value.year,
            self.time.value.month,
            self.time.value.day,
            self.time.value.hour,
            self.time.value.minute,
            lng=self.place.value.longitude if self.place.value else 0.0,
            lat=self.place.value.latitude if self.place.value else 0.0,
            tz_str=self.place.tz if self.place.value else "UTC",
            city=self.place.value.address if self.place.value else "",
            zodiac_type=self.type,
            nation="GB",
        )

    def data(self):
        """Return (object_names, degrees, labels) extracted from computed planets list."""
        object_list = [x["name"] for x in self.computed.planets_list]
        label_list = [x["emoji"] for x in self.computed.planets_list]
        return object_list, self.computed.planets_degrees_ut, label_list

    def report(self):
        """Build a Kerykeion textual Report for the computed subject."""
        if Report is None:
            raise ImportError("Report class is not available in this version of kerykeion")
        return Report(self.computed)


def compute_subject(name: str, dt_str: str, loc_str: str, zodiac: str = "Tropic") -> AstrologicalSubject:
    """Construct a Kerykeion AstrologicalSubject from strings.
    
    Args:
        name: Subject name (human-readable identifier)
        dt_str: Datetime string (parsed by utils.Actual)
        loc_str: Location string (parsed by utils.Actual)
        zodiac: Zodiac type, defaults to "Tropic"
        
    Returns:
        AstrologicalSubject instance with computed positions
    """
    time = Actual(dt_str, t="date")
    place = Actual(loc_str, t="loc")
    return AstrologicalSubject(
        name,
        time.value.year,
        time.value.month,
        time.value.day,
        time.value.hour,
        time.value.minute,
        lng=place.value.longitude if place.value else 0.0,
        lat=place.value.latitude if place.value else 0.0,
        tz_str=place.tz if place.value else "UTC",
        city=place.value.address if place.value else "",
        zodiac_type=zodiac,
        nation="GB"
    )

def extract_kerykeion_points(obj: Any) -> DataFrame:
    """Extract KerykeionPointModel attributes from an object into a DataFrame.
    
    Args:
        obj: Object containing KerykeionPointModel attributes
        
    Returns:
        DataFrame with one row per KerykeionPointModel attribute found
    """
    if KerykeionPointModel is None:
        # KerykeionPointModel not available in this version
        return DataFrame()
    
    data = []
    for attr_name in dir(obj):
        attr = getattr(obj, attr_name)
        if isinstance(attr, KerykeionPointModel):
            data.append(attr.__dict__)
    return DataFrame(data)


# ─────────────────────
# 🔁 COMPOSITE / RELATION CHART
# ─────────────────────

def create_relation_svg(subject1: AstrologicalSubject, subject2: AstrologicalSubject, chart_type: str = "Synastry") -> KerykeionChartSVG:
    """Create a Kerykeion SVG chart for relation/composite types.
    
    Args:
        subject1: First astrological subject
        subject2: Second astrological subject
        chart_type: Type of relation chart (e.g., "Synastry", "Composite"), defaults to "Synastry"
        
    Returns:
        KerykeionChartSVG instance with generated SVG chart
    """
    chart = KerykeionChartSVG(subject1, chart_type=chart_type, second_obj=subject2)
    chart.makeSVG()
    return chart


# ─────────────────────
# 🔺 ASPECT DETECTION
# ─────────────────────

def compute_aspects(bodies: List[CelestialBody], aspect_defs: List[AspectDefinition]) -> List[Aspect]:
    """Compute aspects between celestial bodies using provided definitions.
    
    Args:
        bodies: List of celestial bodies to compute aspects for
        aspect_defs: List of aspect definitions to use for detection
        
    Returns:
        List of Aspect objects representing detected aspects
    """
    aspects = []
    
    if not bodies or not aspect_defs:
        return aspects
    
    # Build a map of aspect definitions by angle for quick lookup
    aspect_by_angle: Dict[float, AspectDefinition] = {}
    for asp_def in aspect_defs:
        aspect_by_angle[asp_def.angle] = asp_def
    
    # Compare all pairs of bodies
    for i, body1 in enumerate(bodies):
        for j, body2 in enumerate(bodies[i+1:], start=i+1):
            # Get longitudes
            lon1 = body1.degree
            lon2 = body2.degree
            
            # Compute angular distance (shortest arc, always positive)
            angle_diff = abs(lon1 - lon2)
            if angle_diff > 180.0:
                angle_diff = DEGREES_IN_CIRCLE - angle_diff
            
            # Check each aspect definition
            for asp_def in aspect_defs:
                exact_angle = asp_def.angle
                orb = asp_def.default_orb
                
                # Normalize exact_angle to 0-180° range (aspects are symmetric)
                if exact_angle > 180.0:
                    exact_angle_normalized = DEGREES_IN_CIRCLE - exact_angle
                else:
                    exact_angle_normalized = exact_angle
                
                # Check if the angle difference is within orb of the exact aspect
                # angle_diff is already in 0-180° range (shortest arc)
                diff_to_exact = abs(angle_diff - exact_angle_normalized)
                
                if diff_to_exact <= orb:
                    # Found an aspect
                    aspect = Aspect(
                        type=asp_def.id,
                        source_id=body1.id,
                        target_id=body2.id,
                        angle=angle_diff,
                        orb=diff_to_exact
                    )
                    aspects.append(aspect)
                    break  # Only record one aspect per pair (the first match)
    
    return aspects


def compute_aspects_for_chart(
    chart: ChartInstance,
    aspect_definitions: Optional[List[AspectDefinition]] = None,
    ws: Optional['Workspace'] = None
) -> List[Dict[str, Any]]:
    """Compute aspects between celestial bodies in a chart.
    
    Args:
        chart: ChartInstance to compute aspects for
        aspect_definitions: List of aspect definitions (orbs, types)
                          If None, uses chart.config.aspect_orbs or workspace defaults
        ws: Optional workspace for default aspect definitions
    
    Returns:
        List of aspect dictionaries, each with:
        {
            'from': str,  # Source object ID (e.g., 'sun')
            'to': str,    # Target object ID (e.g., 'moon')
            'type': str,  # Aspect type: 'conjunction', 'sextile', 'square', 'trine', 'opposition'
            'angle': float,  # Actual angle between objects (degrees)
            'orb': float,    # Orb (deviation from exact aspect, degrees)
            'exact_angle': float,  # Exact aspect angle (0, 60, 90, 120, 180)
            'applying': bool,  # True if aspect is applying (getting closer)
            'separating': bool  # True if aspect is separating
        }
    """
    # Get positions for the chart
    positions = compute_positions_for_chart(chart, ws=ws)
    
    if not positions:
        return []
    
    # Convert positions to CelestialBody objects
    # Extract longitude from position data (handle both float and dict formats)
    bodies: List[CelestialBody] = []
    for obj_id, pos_data in positions.items():
        if isinstance(pos_data, dict):
            longitude = pos_data.get('longitude', 0.0)
        else:
            longitude = float(pos_data)
        
        # Create a CelestialBody object (we need to get definition_id from somewhere)
        # For now, use obj_id as definition_id
        body = CelestialBody(
            id=obj_id,
            definition_id=obj_id,
            degree=longitude,
            sign="",  # Sign would need to be computed from longitude
            retrograde=False,  # Would need speed data to determine
            speed=0.0  # Would need to compute from two positions
        )
        bodies.append(body)
    
    # Get aspect definitions
    if aspect_definitions is None:
        # Try to get from chart config
        cfg = _safe_get_attr(chart, 'config')
        aspect_orbs = _safe_get_attr(cfg, 'aspect_orbs') if cfg else None
        
        # Get aspect definitions from workspace/model
        aspect_definitions = []
        if ws:
            try:
                model = get_active_model(ws)
                if model:
                    # Get aspect definitions from model
                    aspect_definitions = list(getattr(model, 'aspect_definitions', []) or [])
                    
                    # Apply orb overrides from chart config
                    if aspect_orbs:
                        # Create new aspect definitions with overridden orbs
                        updated_defs = []
                        for asp_def in aspect_definitions:
                            if asp_def.id in aspect_orbs:
                                # Create new definition with overridden orb
                                new_orb = float(aspect_orbs[asp_def.id])
                                updated_def = AspectDefinition(
                                    id=asp_def.id,
                                    glyph=asp_def.glyph,
                                    angle=asp_def.angle,
                                    default_orb=new_orb,
                                    i18n=asp_def.i18n,
                                    color=asp_def.color,
                                    importance=asp_def.importance,
                                    line_style=asp_def.line_style,
                                    line_width=asp_def.line_width,
                                    show_label=asp_def.show_label,
                                    valid_contexts=asp_def.valid_contexts
                                )
                                updated_defs.append(updated_def)
                            else:
                                updated_defs.append(asp_def)
                        aspect_definitions = updated_defs
            except Exception as e:
                logger.warning("Could not get aspect definitions from workspace: %s", e)
        
        # If still no definitions, use defaults
        if not aspect_definitions:
            try:
                from module.workspace import get_all_aspect_definitions
                # Get aspects from workspace/model YAML, not SQLite
                all_aspects = get_all_aspect_definitions(ws=ws, model=model)
                aspect_definitions = list(all_aspects.values())
            except Exception:
                # Fallback: create basic aspect definitions
                aspect_definitions = [
                    AspectDefinition(id='conjunction', glyph='☌', angle=0.0, default_orb=8.0, i18n={}),
                    AspectDefinition(id='opposition', glyph='☍', angle=180.0, default_orb=8.0, i18n={}),
                    AspectDefinition(id='trine', glyph='△', angle=120.0, default_orb=8.0, i18n={}),
                    AspectDefinition(id='square', glyph='□', angle=90.0, default_orb=8.0, i18n={}),
                    AspectDefinition(id='sextile', glyph='⚹', angle=60.0, default_orb=6.0, i18n={}),
                ]
    
    # Compute aspects
    aspects = compute_aspects(bodies, aspect_definitions)
    
    # Convert Aspect objects to dictionaries
    result = []
    for aspect in aspects:
        # Find the aspect definition to get exact angle
        exact_angle = 0.0
        for asp_def in aspect_definitions:
            if asp_def.id == aspect.type:
                exact_angle = asp_def.angle
                break
        
        # Determine applying/separating
        # For now, set both to False (would need speed data to determine accurately)
        # Applying means the faster body is catching up to the slower one
        # Separating means they're moving apart
        applying = False
        separating = False
        
        # Try to determine from speeds if available
        body1 = next((b for b in bodies if b.id == aspect.source_id), None)
        body2 = next((b for b in bodies if b.id == aspect.target_id), None)
        if body1 and body2:
            # If we have speed data, we could determine applying/separating
            # For now, we'll leave it as False/False
            pass
        
        result.append({
            'from': aspect.source_id,
            'to': aspect.target_id,
            'type': aspect.type,
            'angle': float(aspect.angle),
            'orb': float(aspect.orb),
            'exact_angle': float(exact_angle),
            'applying': applying,
            'separating': separating
        })
    
    return result


# ─────────────────────
# 🧬 MODEL MERGING
# ─────────────────────

def merge_model_with_overrides(model: AstroModel, overrides: Optional[ModelOverrides]) -> AstroModel:
    """Return a new AstroModel with selective overrides applied.
    
    Applies:
    - OverrideEntry for aspects: glyph/angle/default_orb overrides
    - OverrideEntry for points: glyph overrides and computed flag (if applicable)
    - override_orbs: map of aspect-id -> orb to override AspectDefinition.default_orb
    
    This function does not mutate the original model; it returns a modified copy.
    
    Args:
        model: Base AstroModel to apply overrides to
        overrides: Optional ModelOverrides containing override definitions
        
    Returns:
        New AstroModel instance with overrides applied
    """
    if not overrides:
        return model

    m = deepcopy(model)

    # Index helpers
    aspect_by_id: Dict[str, AspectDefinition] = {a.id: a for a in m.aspect_definitions}
    body_by_id: Dict[str, BodyDefinition] = {b.id: b for b in m.body_definitions}

    # Apply aspect overrides
    for oe in getattr(overrides, 'aspects', []) or []:
        a = aspect_by_id.get(oe.id)
        if not a:
            continue
        # Rebuild AspectDefinition with overrides
        new_angle = oe.angle if oe.angle is not None else a.angle
        new_orb = oe.default_orb if oe.default_orb is not None else a.default_orb
        new_glyph = oe.glyph if oe.glyph is not None else a.glyph
        new_i18n = oe.i18n if oe.i18n is not None else a.i18n
        aspect_by_id[oe.id] = AspectDefinition(id=a.id, glyph=new_glyph, angle=new_angle, default_orb=new_orb, i18n=new_i18n)
    m.aspect_definitions = list(aspect_by_id.values())

    # Apply point overrides (glyph only; computed flag is metadata not present on BodyDefinition)
    for oe in getattr(overrides, 'points', []) or []:
        b = body_by_id.get(oe.id)
        if not b:
            continue
        new_glyph = oe.glyph if oe.glyph is not None else b.glyph
        new_formula = b.formula  # angle/element/avg_speed/max_orb are part of definition; only glyph/i18n commonly overridden
        new_element = b.element
        new_avg = b.avg_speed
        new_max_orb = b.max_orb
        new_i18n = oe.i18n if oe.i18n is not None else b.i18n
        body_by_id[oe.id] = BodyDefinition(
            id=b.id,
            glyph=new_glyph,
            formula=new_formula,
            element=new_element,
            avg_speed=new_avg,
            max_orb=new_max_orb,
            i18n=new_i18n,
        )
    m.body_definitions = list(body_by_id.values())

    # Apply override_orbs map
    orb_map = getattr(overrides, 'override_orbs', {}) or {}
    if orb_map:
        new_aspects: List[AspectDefinition] = []
        for a in m.aspect_definitions:
            if a.id in orb_map:
                new_aspects.append(AspectDefinition(id=a.id, glyph=a.glyph, angle=a.angle, default_orb=float(orb_map[a.id]), i18n=a.i18n))
            else:
                new_aspects.append(a)
        m.aspect_definitions = new_aspects

    return m


def _build_aspect_orbs(model: AstroModel) -> Dict[str, float]:
    """Create a map aspect-id -> default orb from the model's aspect definitions.
    
    Args:
        model: AstroModel containing aspect definitions
        
    Returns:
        Dictionary mapping aspect ID to default orb value
    """
    return {a.id: float(a.default_orb) for a in getattr(model, 'aspect_definitions', []) or []}


def get_active_model(ws: Optional['Workspace']) -> Optional[AstroModel]:
    """Resolve the currently active AstroModel instance from a Workspace, if available.
    
    Falls back to first model if no active model is specified.
    
    Args:
        ws: Workspace instance to get active model from
        
    Returns:
        Active AstroModel instance, or None if no models available
    """
    if ws is None:
        return None
    models = getattr(ws, 'models', {}) or {}
    if not models:
        return None
    # Get active model name
    name = getattr(ws, 'active_model', None)
    if name and name in models:
        return models[name]
    # Fallback: return first available model
    try:
        return next(iter(models.values()))
    except StopIteration:
        return None


def resolve_effective_defaults(ws: 'Workspace', model: Optional[AstroModel]) -> Dict[str, object]:
    """Resolve effective defaults merging workspace overrides on top of AstroModel settings.
    
    Args:
        ws: Workspace containing default overrides
        model: Optional AstroModel with base settings
        
    Returns:
        Dictionary with keys: house_system, bodies, aspects, standard_orb, engine,
        zodiac_type, ayanamsa, aspect_orbs, observable_objects
    """
    out: Dict[str, object] = {}
    if model is None:
        return out

    ms = getattr(model, 'settings', None)
    d = getattr(ws, 'default', None) if ws is not None else None

    # House system
    out['house_system'] = getattr(d, 'default_house_system', None) or (getattr(ms, 'default_house_system', None) if ms else None)

    # Bodies (from model settings)
    ws_bodies = getattr(d, 'default_bodies', None) if d else None
    out['bodies'] = ws_bodies or (getattr(ms, 'default_bodies', None) if ms else None) or []

    # Observable objects (extends bodies with angles, houses, etc.)
    ws_observable = getattr(d, 'observable_objects', None) if d else None
    # Merge with bodies if both exist
    if ws_observable:
        combined = list(set((out.get('bodies') or []) + ws_observable))
        out['observable_objects'] = combined
    else:
        out['observable_objects'] = out.get('bodies') or []

    # Aspects: prefer top-level ws.aspects, then defaults override, then model settings
    ws_aspects_top = getattr(ws, 'aspects', []) if ws is not None else []
    if ws_aspects_top:
        out['aspects'] = ws_aspects_top
    else:
        ws_aspects = getattr(d, 'default_aspects', None) if d else None
        out['aspects'] = ws_aspects or (getattr(ms, 'default_aspects', None) if ms else None) or []

    # Standard orb (from model settings)
    out['standard_orb'] = getattr(ms, 'standard_orb', None) if ms else None

    # Engine prefs (workspace default can override model engine)
    out['engine'] = (getattr(d, 'ephemeris_engine', None) if d else None) or getattr(model, 'engine', None)
    out['zodiac_type'] = getattr(model, 'zodiac_type', None)
    out['ayanamsa'] = getattr(model, 'ayanamsa', None)

    # Aspect orbs map from model
    out['aspect_orbs'] = _build_aspect_orbs(model)
    return out


def compute_positions(engine: Optional[EngineType], name: str, dt_str: str, loc_str: str,
                      ephemeris_path: Optional[str] = None, requested_objects: Optional[List[str]] = None) -> Dict[str, float]:
    """Dispatch position computation based on engine.
    - For EngineType.JPL, returns a dict of ecliptic longitudes using Skyfield and a local ephemeris file.
    - For other or None, returns Kerykeion observable object longitudes (degrees) as a dict.
    
    Args:
        engine: Computation engine to use
        name: Subject name
        dt_str: Datetime string
        loc_str: Location string
        ephemeris_path: Optional path to ephemeris file
        requested_objects: Optional list of object IDs to compute (filters results)
    
    Returns:
        Dict mapping object_id -> ecliptic_longitude (degrees). Empty dict on error.
        
    Raises:
        ValueError: If datetime or location cannot be parsed
        FileNotFoundError: If ephemeris file is specified but not found
    """
    if engine == EngineType.JPL:
        result = compute_jpl_positions(name, dt_str, loc_str, ephemeris_path=ephemeris_path, requested_objects=requested_objects)
        # Ensure we return a dict, not a string
        if isinstance(result, dict):
            # For JPL, we only get planets; angles/houses need kerykeion fallback
            jpl_positions = result
            
            # If requested objects include non-planets, fall through to kerykeion
            non_planet_objects = []
            if requested_objects:
                jpl_planets = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]
                non_planet_objects = [obj for obj in requested_objects if obj not in jpl_planets]
            
            if non_planet_objects:
                # Get additional objects from kerykeion
                try:
                    subj = compute_subject(name, dt_str, loc_str)
                    # Get model for constants (degrees_in_circle)
                    model = None
                    try:
                        model = get_active_model(None)
                    except Exception:
                        pass
                    kerykeion_positions = _extract_kerykeion_observable_objects(subj, requested_objects=non_planet_objects, model=model)
                    jpl_positions.update(kerykeion_positions)
                except (ValueError, AttributeError, KeyError) as e:
                    logger.warning("Could not compute non-planet objects with Kerykeion: %s", e)
            
            return jpl_positions
        else:
            # If JPL failed, fall through to Kerykeion
            pass
    
    # Kerykeion: extract all observable objects
    try:
        subj = compute_subject(name, dt_str, loc_str)
        # Try using Subject wrapper's data() method first (it knows how to access planets_list)
        positions = {}
        mapping = _get_kerykeion_object_mapping()
        try:
            subject_wrapper = Subject(name)
            subject_wrapper.computed = subj
            object_list, degrees_list, labels = subject_wrapper.data()
            # If we got data from Subject.data(), use it
            if object_list and degrees_list and len(object_list) == len(degrees_list):
                for i, obj_name in enumerate(object_list):
                    if i < len(degrees_list):
                        obj_id = mapping.get(obj_name.lower(), obj_name.lower())
                        if requested_objects and obj_id not in requested_objects and obj_name.lower() not in requested_objects:
                            continue
                        try:
                            # Normalize to [0, 360) range (same as JPL)
                            lon_float = float(degrees_list[i])
                            normalized_lon = lon_float % DEGREES_IN_CIRCLE
                            if normalized_lon < 0:
                                normalized_lon += DEGREES_IN_CIRCLE
                            positions[obj_id] = normalized_lon
                        except (ValueError, TypeError, IndexError) as e:
                            logger.debug("Failed to normalize position for %s: %s", obj_name, e)
                            continue
            else:
                logger.debug("Subject.data() returned empty or mismatched lists: objects=%s, degrees=%s", 
                           len(object_list) if object_list else 0, len(degrees_list) if degrees_list else 0)
        except Exception as e:
            logger.debug("Subject wrapper failed, falling back to direct extraction: %s", e)
        
        # Also try direct extraction as fallback
        # Get active model for constants (degrees_in_circle)
        model = None
        try:
            model = get_active_model(None)  # We don't have workspace here, but model might be available
        except Exception:
            pass
        
        if not positions:
            positions = _extract_kerykeion_observable_objects(subj, requested_objects=requested_objects, model=model)
            if not positions:
                # Add diagnostic logging
                logger.debug("Direct extraction also failed. Checking Kerykeion subject attributes:")
                logger.debug("  has planets_list: %s", hasattr(subj, 'planets_list'))
                logger.debug("  has planets_degrees_ut: %s", hasattr(subj, 'planets_degrees_ut'))
                if hasattr(subj, 'planets_list'):
                    logger.debug("  planets_list type: %s, length: %s", type(subj.planets_list), 
                               len(subj.planets_list) if isinstance(subj.planets_list, list) else 'N/A')
                if hasattr(subj, 'planets_degrees_ut'):
                    logger.debug("  planets_degrees_ut type: %s, length: %s", type(subj.planets_degrees_ut),
                               len(subj.planets_degrees_ut) if isinstance(subj.planets_degrees_ut, list) else 'N/A')
                # Try to list available attributes
                available_attrs = [attr for attr in dir(subj) if not attr.startswith('_') and hasattr(getattr(subj, attr, None), '__class__')]
                logger.debug("  Available planet-like attributes: %s", available_attrs[:10])
        else:
            # Merge with direct extraction for additional objects (angles, houses, etc.)
            positions_from_extract = _extract_kerykeion_observable_objects(subj, requested_objects=requested_objects, model=model)
            for k, v in positions_from_extract.items():
                if k not in positions:  # Don't overwrite if already set from Subject.data()
                    positions[k] = v
        if not positions:
            logger.warning("_extract_kerykeion_observable_objects returned empty dict for %s at %s in %s", name, dt_str, loc_str)
        return positions
    except (ValueError, AttributeError, KeyError) as e:
        # Log specific errors for debugging
        logger.error("Error computing positions with Kerykeion: %s", e, exc_info=True)
        return {}
    except Exception as e:
        # Catch-all for unexpected errors
        logger.error("Unexpected error computing positions: %s", e, exc_info=True)
        return {}


def compute_positions_for_chart(
    chart: ChartInstance, 
    ws: Optional['Workspace'] = None,
    include_physical: bool = False,
    include_topocentric: bool = False
) -> Dict[str, Union[float, Dict[str, float]]]:
    """Compute positions using a ChartInstance's engine and ephemeris settings.
    Uses chart.subject.event_time and chart.subject.location.name for location lookup.
    Handles both ChartInstance objects and dict-like structures safely.
    
    Args:
        chart: ChartInstance to compute positions for
        ws: Optional workspace for resolving observable objects defaults
        include_physical: If True, include magnitude/phase/elongation (JPL only)
        include_topocentric: If True, include altitude/azimuth (JPL with location)
        
    Returns:
        Dict mapping object_id -> position data:
        - For non-JPL engines: float (longitude in degrees)
        - For JPL engine: dict with keys:
            - 'longitude': float (degrees) - always present
            - 'latitude': float (degrees) - if available
            - 'distance': float (AU) - always present for JPL
            - 'declination': float (degrees) - always present for JPL
            - 'right_ascension': float (degrees) - always present for JPL
            - 'altitude': float (degrees) - if include_topocentric and location available
            - 'azimuth': float (degrees) - if include_topocentric and location available
            - 'apparent_magnitude': float - if include_physical
            - 'phase_angle': float (degrees) - if include_physical
            - 'elongation': float (degrees) - if include_physical
            - 'light_time': float (seconds) - if include_physical
            - 'speed': float (degrees/day) - if available
            - 'retrograde': bool - if available
        
    Raises:
        ValueError: If chart is missing required subject or location data
    """
    # Get engine and ephemeris from config
    cfg = _safe_get_attr(chart, 'config')
    engine = _safe_get_attr(cfg, 'engine') if cfg else None
    eph = _safe_get_attr(cfg, 'override_ephemeris') if cfg else None
    
    # If engine is None but override_ephemeris is set, infer that we should use JPL
    if engine is None and eph:
        engine = EngineType.JPL
    
    # SWISSEPH doesn't use BSP files - clear ephemeris path if engine is SWISSEPH
    # BSP files are only for JPL/Skyfield engine
    if engine == EngineType.SWISSEPH:
        eph = None
    
    # Get observable objects: prefer chart config, then workspace defaults, then model defaults
    requested_objects = _safe_get_attr(cfg, 'observable_objects') if cfg else None
    if not requested_objects and ws:
        try:
            model = get_active_model(ws)
            if model:
                eff = resolve_effective_defaults(ws, model)
                requested_objects = eff.get('observable_objects')
        except (AttributeError, KeyError, TypeError) as e:
            # Log but don't fail - use None as fallback (will compute all objects)
            logger.warning("Could not resolve observable objects from workspace: %s", e)
    
    
    # Get subject data safely
    subj = _safe_get_attr(chart, 'subject')
    if subj is None:
        raise ValueError("Chart has no subject")
    
    # Get name - handle both object and dict
    name = _safe_get_attr(subj, 'name')
    if not name:
        # Try alternative access patterns
        if isinstance(subj, dict):
            name = subj.get('name') or subj.get('id') or 'chart'
        else:
            name = 'chart'
    
    # Get event_time
    event_time = _safe_get_attr(subj, 'event_time')
    if event_time is None:
        raise ValueError(f"Chart subject has no event_time (subject type: {type(subj)})")
    # Convert datetime to ISO format string for reliable parsing
    if isinstance(event_time, datetime):
        dt_str = event_time.isoformat()
    else:
        dt_str = str(event_time)
    
    # Get location name - handle both object and dict
    loc = _safe_get_attr(subj, 'location')
    if loc is None:
        raise ValueError("Chart subject has no location")
    
    loc_str = _safe_get_attr(loc, 'name')
    if not loc_str:
        # Try alternative access patterns
        if isinstance(loc, dict):
            loc_str = loc.get('name') or ''
        # If still no name, try to construct from lat/lon if available
        if not loc_str:
            lat = _safe_get_attr(loc, 'latitude')
            lon = _safe_get_attr(loc, 'longitude')
            if lat is not None and lon is not None:
                loc_str = f"{lat},{lon}"
    
    if not loc_str:
        raise ValueError(f"Could not determine location name (location type: {type(loc)})")
    
    # Check if we should use extended format for JPL
    use_extended = (engine == EngineType.JPL)
    
    # Call compute_positions with the extracted parameters
    
    if use_extended:
        # For JPL, use extended format
        result = compute_jpl_positions(
            name, dt_str, loc_str, 
            ephemeris_path=eph, 
            requested_objects=requested_objects,
            include_physical=include_physical,
            include_topocentric=include_topocentric,
            extended=True
        )
        
        # Merge with non-planet objects from kerykeion if needed
        if requested_objects:
            jpl_planets = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]
            non_planet_objects = [obj for obj in requested_objects if obj not in jpl_planets]
            
            if non_planet_objects:
                # Get additional objects from kerykeion (angles, houses, etc.)
                try:
                    subj = compute_subject(name, dt_str, loc_str)
                    # Get model for constants
                    model = None
                    try:
                        model = get_active_model(ws)
                    except Exception:
                        pass
                    kerykeion_positions = _extract_kerykeion_observable_objects(subj, requested_objects=non_planet_objects, model=model)
                    # Kerykeion returns simple floats, but we need to maintain extended format for JPL
                    # For non-planets, we'll keep them as floats (they don't have extended properties)
                    for obj_id, lon in kerykeion_positions.items():
                        if obj_id not in result:
                            result[obj_id] = lon  # Keep as float for non-planets
                except (ValueError, AttributeError, KeyError) as e:
                    logger.warning("Could not compute non-planet objects with Kerykeion: %s", e)
    else:
        # For non-JPL engines, use standard format
        result = compute_positions(engine, name, dt_str, loc_str, ephemeris_path=eph, requested_objects=requested_objects)
    
    # Ensure we return a dict
    if not isinstance(result, dict):
        logger.warning("compute_positions returned non-dict: %s = %s", type(result), result)
        return {}
    
    # Return empty dict if no positions found
    if not result:
        logger.warning("compute_positions returned empty dict for %s at %s in %s", name, dt_str, loc_str)
        return {}
    
    return result


# ─────────────────────
# 📦 HIGHER-LEVEL APP SERVICES (UI-agnostic)
# ─────────────────────

def build_chart_instance(name: str, dt_str: str, loc_text: str,
                         mode: ChartMode, ws: Optional[Workspace] = None, 
                         ephemeris_path: Optional[str] = None) -> ChartInstance:
    """Build a ChartInstance using workspace defaults when provided.
    - Resolves engine and house system from ws if available.
    - Uses utils.prepare_horoscope to produce a fully-typed ChartInstance.
    """
    # Resolve engine and model-based defaults
    engine = None
    house = None
    zodiac_type = None
    included_points: List[str] = []
    observable_objects: Optional[List[str]] = None
    aspect_orbs: Dict[str, float] = {}
    ayanamsa = None

    if ws is not None:
        try:
            # Workspace default engine override
            d = getattr(ws, 'default', None)
            engine = getattr(d, 'ephemeris_engine', None)
        except Exception:
            pass
        # Resolve effective defaults from active model
        try:
            model = get_active_model(ws)
            if model is not None:
                eff_model = merge_model_with_overrides(model, getattr(ws, 'model_overrides', None))
                eff = resolve_effective_defaults(ws, eff_model)
                house = eff.get('house_system') or house
                zodiac_type = eff.get('zodiac_type') or zodiac_type
                included_points = list(eff.get('bodies') or [])
                observable_objects = list(eff.get('observable_objects') or [])
                aspect_orbs = dict(eff.get('aspect_orbs') or {})
                ayanamsa = eff.get('ayanamsa') or ayanamsa
                # If workspace default specifies engine, that already took priority above; otherwise use model engine
                engine = engine or eff.get('engine')
        except (AttributeError, KeyError, TypeError) as e:
            # Best-effort: if anything fails, continue with minimal defaults
            logger.warning("Could not resolve all defaults from workspace/model: %s", e)
 
    # Normalize inputs via utils.Actual and to_model_location
    try:
        t = Actual(dt_str, t="date").value
        loc_model = Actual(loc_text, t="loc").to_model_location()
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Failed to parse date or location: {e}") from e
    
    # Delegate to prepare_horoscope (ensures ChartSubject/ChartConfig types)
    chart = prepare_horoscope(name=name, dt=t, loc=loc_model, engine=engine,
                              ephemeris_path=ephemeris_path, house=house)
    try:
        chart.config.mode = mode
    except AttributeError:
        # ChartConfig might not support mode assignment directly
        pass
    
    # Apply additional resolved defaults onto ChartConfig
    try:
        if house is not None:
            chart.config.house_system = house
        if zodiac_type is not None:
            chart.config.zodiac_type = zodiac_type
        if included_points:
            chart.config.included_points = included_points
        if observable_objects:
            chart.config.observable_objects = observable_objects
        if aspect_orbs:
            chart.config.aspect_orbs = aspect_orbs
        if engine is not None:
            chart.config.engine = engine
        if ayanamsa is not None:
            chart.config.ayanamsa = ayanamsa
    except AttributeError as e:
        logger.warning("Could not set all chart config defaults: %s", e)
    
    return chart


def find_chart_by_name_or_id(ws: Optional[Workspace], name_or_id: str) -> Optional[ChartInstance]:
    """Find a chart in the workspace by subject name or chart ID.
    
    Args:
        ws: Workspace to search in
        name_or_id: Subject name or chart ID to search for
        
    Returns:
        ChartInstance if found, None otherwise
    """
    if not ws or not getattr(ws, 'charts', None):
        return None
    key = (name_or_id or '').strip()
    for c in ws.charts:
        subj = getattr(c, 'subject', None)
        cid = getattr(c, 'id', None)
        nm = getattr(subj, 'name', None) if subj else None
        if key and (key == nm or key == cid):
            return c
    return None


def search_charts(ws: Optional[Workspace], query: str) -> List[ChartInstance]:
    """Search charts in workspace using case-insensitive text matching.
    
    Searches across chart name, event_time, location name, and tags.
    
    Args:
        ws: Workspace to search in
        query: Search query string
        
    Returns:
        List of ChartInstance objects matching the query
    """
    if not ws or not getattr(ws, 'charts', None):
        return []
    q = (query or '').strip().lower()
    if not q:
        return list(ws.charts)
    out: List[ChartInstance] = []
    for ch in ws.charts:
        try:
            subj = getattr(ch, 'subject', None)
            loc = getattr(subj, 'location', None) if subj else None
            tags = getattr(ch, 'tags', []) or []
            hay = " ".join([
                str(getattr(subj, 'name', '') or ''),
                str(getattr(subj, 'event_time', '') or ''),
                str(getattr(loc, 'name', '') or ''),
                ",".join([str(t) for t in tags])
            ]).lower()
            if q in hay:
                out.append(ch)
        except Exception:
            continue
    return out


def list_open_view_rows(ws: Optional[Workspace]) -> List[Dict[str, str]]:
    """Produce table rows for Open view display.
    
    Args:
        ws: Workspace containing charts
        
    Returns:
        List of dictionaries with keys: name, event_time, location, tags, search_text
    """
    rows: List[Dict[str, str]] = []
    if not ws or not getattr(ws, 'charts', None):
        return rows
    for ch in ws.charts:
        try:
            subj = getattr(ch, 'subject', None)
            loc = getattr(subj, 'location', None) if subj else None
            name = getattr(subj, 'name', '') if subj else ''
            event_time = str(getattr(subj, 'event_time', '') or '')
            location_name = getattr(loc, 'name', '') if loc else ''
            tags = ", ".join(getattr(ch, 'tags', []) or [])
            # Get chart type from config
            cfg = getattr(ch, 'config', None)
            chart_type = ''
            if cfg:
                mode = getattr(cfg, 'mode', None)
                if mode:
                    chart_type = mode.value if hasattr(mode, 'value') else str(mode)
            search_text = f"{name} {chart_type} {event_time} {location_name} {tags}".lower()
            rows.append({
                'name': name,
                'chart_type': chart_type,
                'event_time': event_time,
                'location': location_name,
                'tags': tags,
                'search_text': search_text,
            })
        except Exception:
            continue
    return rows


def build_radix_figure_for_chart(chart: ChartInstance, engine_override: Optional[EngineType] = None, 
                                 ephemeris_path_override: Optional[str] = None, ws: Optional['Workspace'] = None) -> Any:
    """Extract positions from a ChartInstance's computed_chart and return a Plotly Figure ready to render.
    
    Always recomputes positions to ensure accuracy, as stored computed_chart may contain
    initial/default values that are incorrect.
    
    Args:
        chart: ChartInstance to compute positions for
        engine_override: Optional engine to use instead of chart's stored engine
        ephemeris_path_override: Optional ephemeris path to use instead of chart's stored path
        ws: Optional workspace for resolving observable objects defaults
        
    Returns:
        Plotly Figure object ready for rendering
    """
    # Always recompute positions to ensure we have accurate, up-to-date values
    # The computed_chart may contain stale or initial values
    # Use override engine if provided, otherwise use chart's stored engine
    if engine_override is not None or ephemeris_path_override is not None:
        # Get observable objects: prefer chart config, then workspace defaults, then model defaults
        cfg = _safe_get_attr(chart, 'config')
        requested_objects = _safe_get_attr(cfg, 'observable_objects') if cfg else None
        if not requested_objects and ws:
            try:
                model = get_active_model(ws)
                if model:
                    eff = resolve_effective_defaults(ws, model)
                    requested_objects = eff.get('observable_objects')
            except (AttributeError, KeyError, TypeError) as e:
                # Log but don't fail - use None as fallback (will compute all objects)
                logger.warning("Could not resolve observable objects from workspace: %s", e)
        
        subj = _safe_get_attr(chart, 'subject')
        name = _safe_get_attr(subj, 'name') or 'chart'
        event_time = _safe_get_attr(subj, 'event_time')
        # Convert datetime to ISO format string for reliable parsing
        if isinstance(event_time, datetime):
            dt_str = event_time.isoformat()
        else:
            dt_str = str(event_time) if event_time else ''
        loc = _safe_get_attr(subj, 'location')
        loc_str = _safe_get_attr(loc, 'name') or '' if loc else ''
        if not loc_str and loc:
            lat = _safe_get_attr(loc, 'latitude')
            lon = _safe_get_attr(loc, 'longitude')
            if lat is not None and lon is not None:
                loc_str = f"{lat},{lon}"
        
        positions = compute_positions(engine_override, name, dt_str, loc_str, 
                                     ephemeris_path=ephemeris_path_override, 
                                     requested_objects=requested_objects)
    else:
        positions = compute_positions_for_chart(chart, ws=ws)
    
    # Verify we got valid positions (not all zeros or suspiciously clustered)
    if not positions:
        # If no positions, log error and return empty figure with warning
        logger.error("build_radix_figure_for_chart got empty positions for chart %s", _safe_get_attr(chart, 'id', default='unknown'))
        # Return an empty figure rather than crashing
        import plotly.graph_objects as go
        empty_fig = go.Figure()
        empty_fig.add_annotation(
            text="No positions computed. Check chart data and computation engine settings.",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="red")
        )
        return empty_fig
    
    values = list(positions.values())
    # Check if all values are suspiciously close to 0 (within -5 to 5 degrees)
    all_near_zero = all(abs(v) < 5.0 for v in values)
    if all_near_zero:
        # This suggests the computation might be using wrong parameters
        # But we'll still render it - the user can see the issue
        import warnings
        warnings.warn(
            f"All computed positions are near 0° (within -5° to 5°). "
            f"This may indicate incorrect time/location parameters. "
            f"Positions: {positions}"
        )
    
    return build_radix_figure(positions)


def compute_positions_for_inputs(engine: Optional[EngineType], name: str,
                                 dt_str: str, loc_text: str,
                                 ephemeris_path: Optional[str] = None,
                                 requested_objects: Optional[List[str]] = None) -> Dict[str, float]:
    """Thin wrapper over compute_positions to normalize/forward parameters from UI layers."""
    return compute_positions(engine, name, dt_str, loc_text, ephemeris_path=ephemeris_path, requested_objects=requested_objects)