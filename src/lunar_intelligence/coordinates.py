"""Lunar site coordinates, body-fixed cartesian conversion, and topocentric ENU frames."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TypeAlias

from .config import MOON_MEAN_RADIUS_M, ModelConfig

Vector3: TypeAlias = tuple[float, float, float]


def dot(a: Vector3, b: Vector3) -> float:
    """Compute dot product of two 3D vectors."""
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Vector3, b: Vector3) -> Vector3:
    """Compute cross product of two 3D vectors."""
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def norm(vector: Vector3) -> float:
    """Compute Euclidean norm (magnitude) of a 3D vector."""
    return math.sqrt(dot(vector, vector))


def unit(vector: Vector3) -> Vector3:
    """Compute unit vector in the direction of the given vector."""
    magnitude = norm(vector)
    if not math.isfinite(magnitude) or magnitude <= 0:
        raise ValueError("A finite, non-zero vector is required for unit normalization")
    return (vector[0] / magnitude, vector[1] / magnitude, vector[2] / magnitude)


@dataclass(frozen=True)
class LunarSite:
    """A lunar landing site specified in planetocentric coordinates."""

    latitude_deg: float
    longitude_deg: float
    elevation_m: float = 0.0
    site_id: str = "UNSPECIFIED"
    name: str = ""
    region: str = "South Pole"
    description: str = ""
    mean_slope_deg: float = 5.0
    roughness_score: float = 0.2  # 0 (smooth) to 1.0 (extremely rough)
    scientific_priority: float = 0.8  # 0 to 1.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.latitude_deg) or not -90.0 <= self.latitude_deg <= 90.0:
            raise ValueError(f"latitude_deg must be in [-90, 90], got {self.latitude_deg}")
        if not math.isfinite(self.longitude_deg):
            raise ValueError("longitude_deg must be finite")
        if not math.isfinite(self.elevation_m):
            raise ValueError("elevation_m must be finite")

    @property
    def east_longitude_deg(self) -> float:
        """East-positive longitude in [0, 360)."""
        return self.longitude_deg % 360.0

    @property
    def signed_longitude_deg(self) -> float:
        """Signed longitude in [-180, 180]."""
        lon = self.longitude_deg % 360.0
        return lon if lon <= 180.0 else lon - 360.0


@dataclass(frozen=True)
class LocalFrame:
    """Orthonormal local topocentric basis (East, North, Up).

    Azimuth is measured clockwise from North (0° = North, 90° = East, 180° = South, 270° = West).
    Elevation is measured above the local horizontal plane (-90° to +90°).
    """

    east: Vector3
    north: Vector3
    up: Vector3

    def direction_angles(self, vector: Vector3) -> tuple[float, float]:
        """Compute (elevation_deg, azimuth_deg) for a vector in this local frame."""
        u = unit(vector)
        # Up component gives sin(elevation)
        up_comp = max(-1.0, min(1.0, dot(u, self.up)))
        elevation = math.degrees(math.asin(up_comp))

        # Project into local horizontal plane
        e_comp = dot(u, self.east)
        n_comp = dot(u, self.north)

        if abs(e_comp) < 1e-15 and abs(n_comp) < 1e-15:
            azimuth = 0.0
        else:
            azimuth = math.degrees(math.atan2(e_comp, n_comp)) % 360.0

        return elevation, azimuth


def local_enu(site: LunarSite) -> LocalFrame:
    """Construct an orthonormal East-North-Up frame at the lunar site."""
    lat_rad = math.radians(site.latitude_deg)
    lon_rad = math.radians(site.longitude_deg)

    cos_lat = math.cos(lat_rad)
    sin_lat = math.sin(lat_rad)
    cos_lon = math.cos(lon_rad)
    sin_lon = math.sin(lon_rad)

    # Local up (outward radial vector)
    up: Vector3 = (cos_lat * cos_lon, cos_lat * sin_lon, sin_lat)

    # Polar singularities handling
    if abs(cos_lat) < 1e-12:
        # At exact pole: define east along 90° meridian for North Pole, -90° for South Pole
        if site.latitude_deg > 0:
            east: Vector3 = (0.0, 1.0, 0.0)
            north: Vector3 = (-1.0, 0.0, 0.0)
        else:
            east: Vector3 = (0.0, 1.0, 0.0)
            north: Vector3 = (1.0, 0.0, 0.0)
    else:
        # East: tangent to parallel of latitude in direction of increasing longitude
        east = (-sin_lon, cos_lon, 0.0)
        # North: up cross east
        north = cross(up, east)

    return LocalFrame(east=unit(east), north=unit(north), up=unit(up))


def site_position_body_fixed(site: LunarSite, config: ModelConfig | None = None) -> Vector3:
    """Compute Cartesian position vector (in meters) of the site in the lunar body-fixed frame."""
    radius = (config.moon_radius_m if config else MOON_MEAN_RADIUS_M) + site.elevation_m
    lat_rad = math.radians(site.latitude_deg)
    lon_rad = math.radians(site.longitude_deg)

    return (
        radius * math.cos(lat_rad) * math.cos(lon_rad),
        radius * math.cos(lat_rad) * math.sin(lon_rad),
        radius * math.sin(lat_rad),
    )


def angular_direction(vector_m: Vector3, frame: LocalFrame) -> tuple[float, float, float]:
    """Compute elevation (deg), azimuth (deg), and distance (m) for a vector in a local frame."""
    dist = norm(vector_m)
    if dist == 0.0:
        raise ValueError("Cannot compute angular direction for zero vector")
    elevation, azimuth = frame.direction_angles(vector_m)
    return elevation, azimuth, dist


def effective_horizon_dip_deg(mast_height_m: float, moon_radius_m: float = MOON_MEAN_RADIUS_M) -> float:
    """Compute geometric depression of horizon due to antenna elevation above surface.

    Dip angle = arccos(R / (R + h)) approx sqrt(2 * h / R) in radians.
    """
    if mast_height_m <= 0:
        return 0.0
    ratio = moon_radius_m / (moon_radius_m + mast_height_m)
    return math.degrees(math.acos(max(-1.0, min(1.0, ratio))))


def great_circle_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great circle surface distance on Moon between two points in km."""
    phi1, lambda1 = math.radians(lat1), math.radians(lon1)
    phi2, lambda2 = math.radians(lat2), math.radians(lon2)
    dphi = phi2 - phi1
    dlambda = lambda2 - lambda1
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return (MOON_MEAN_RADIUS_M / 1000.0) * c
