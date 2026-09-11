import React, { useState, useEffect, useRef } from 'react';
import L from 'leaflet';
import {
  MapPin,
  Layers,
  Filter,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ExternalLink,
  Search,
  Eye,
  Info,
} from 'lucide-react';
import { mapApi } from '../api/map';
import { CadastralMapRecord } from '../types';
import { useNavigation } from '../context/NavigationContext';

export const CadastralMap: React.FC = () => {
  const { navigate } = useNavigation();


  // State
  const [parcels, setParcels] = useState<CadastralMapRecord[]>([]);
  const [selectedParcel, setSelectedParcel] = useState<CadastralMapRecord | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [discrepancyOnly, setDiscrepancyOnly] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [showBoundaries, setShowBoundaries] = useState<boolean>(true);
  const [showMarkers, setShowMarkers] = useState<boolean>(true);

  // Leaflet Map Refs
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const layerGroupRef = useRef<L.LayerGroup | null>(null);

  // Load parcel features
  const loadParcels = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await mapApi.getMapParcels({
        status: statusFilter || undefined,
        has_discrepancies: discrepancyOnly ? true : undefined,
        village: searchQuery || undefined,
      });
      setParcels(resp.parcels || []);
      if (selectedParcel) {
        const updated = resp.parcels.find((p) => p.record_id === selectedParcel.record_id);
        setSelectedParcel(updated || null);
      }
    } catch (err: any) {
      console.error('Failed to load cadastral map features:', err);
      setError(err.message || 'Unable to retrieve spatial cadastral records.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadParcels();
  }, [statusFilter, discrepancyOnly]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadParcels();
  };

  // Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (mapInstanceRef.current) return;

    // Default center on India (Rajasthan / MP geographic region)
    const map = L.map(mapContainerRef.current, {
      center: [26.85, 75.8],
      zoom: 12,
      zoomControl: true,
    });

    // Dark high-contrast basemap tiles (CartoDB Dark Matter) with OSM fallback
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
      maxZoom: 19,
    }).addTo(map);

    const layerGroup = L.layerGroup().addTo(map);
    mapInstanceRef.current = map;
    layerGroupRef.current = layerGroup;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
      layerGroupRef.current = null;
    };
  }, []);

  // Update Map Layers when parcels or display toggles change
  useEffect(() => {
    const map = mapInstanceRef.current;
    const layerGroup = layerGroupRef.current;
    if (!map || !layerGroup) return;

    layerGroup.clearLayers();

    if (parcels.length === 0) return;

    const bounds = L.latLngBounds([]);

    parcels.forEach((parcel) => {
      const hasCoords = parcel.latitude != null && parcel.longitude != null;
      const hasGeo = parcel.boundary_geojson != null;

      // Color scheme based on review / status / discrepancies
      let color = '#10b981'; // Emerald for VALIDATED
      if (parcel.has_discrepancies || parcel.status === 'FLAGGED') {
        color = '#ef4444'; // Red for FLAGGED / Discrepant
      } else if (parcel.review_status === 'PENDING_REVIEW' || parcel.status === 'EXTRACTED' || parcel.status === 'NORMALIZED') {
        color = '#f59e0b'; // Amber for PENDING_REVIEW
      }

      // 1. Render Boundary Polygon
      if (showBoundaries && hasGeo) {
        try {
          const geoLayer = L.geoJSON(parcel.boundary_geojson as any, {
            style: {
              color: color,
              weight: selectedParcel?.record_id === parcel.record_id ? 4 : 2,
              fillColor: color,
              fillOpacity: selectedParcel?.record_id === parcel.record_id ? 0.45 : 0.25,
            },
          });

          geoLayer.on('click', () => {
            setSelectedParcel(parcel);
          });

          geoLayer.bindTooltip(
            `<strong>Khasra: ${parcel.khasra_number}</strong><br/>Village: ${parcel.village}<br/>Area: ${parcel.area_in_hectares} Ha`,
            { sticky: true, className: 'cadastral-tooltip' }
          );

          layerGroup.addLayer(geoLayer);
          bounds.extend(geoLayer.getBounds());
        } catch (e) {
          console.warn(`Failed to parse GeoJSON boundary for parcel ${parcel.record_id}`, e);
        }
      }

      // 2. Render Pin Marker
      if (showMarkers && hasCoords) {
        const lat = parcel.latitude!;
        const lon = parcel.longitude!;

        const customIcon = L.divIcon({
          className: 'cadastral-marker-pin',
          html: `<div style="
            width: 28px;
            height: 28px;
            background: ${color};
            border: 2px solid #ffffff;
            border-radius: 50%;
            box-shadow: 0 4px 10px rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            color: #ffffff;
            font-size: 11px;
            font-weight: 700;
          ">${parcel.khasra_number.slice(0, 3)}</div>`,
          iconSize: [28, 28],
          iconAnchor: [14, 14],
        });

        const marker = L.marker([lat, lon], { icon: customIcon });
        marker.on('click', () => {
          setSelectedParcel(parcel);
        });

        marker.bindTooltip(
          `<strong>Khasra ${parcel.khasra_number}</strong> (${parcel.status})`,
          { direction: 'top', offset: [0, -10] }
        );

        layerGroup.addLayer(marker);
        bounds.extend([lat, lon]);
      }
    });

    // Auto-fit map bounds if valid layers exist
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 16 });
    }
  }, [parcels, showBoundaries, showMarkers, selectedParcel]);

  const handleOpenDetail = (recordId: string) => {
    navigate('record-detail', { recordId });
  };


  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '1.25rem' }}>
      {/* Top Header & Overview */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
        }}
      >
        <div>
          <h1
            style={{
              fontSize: '1.75rem',
              fontWeight: 700,
              color: 'var(--text-primary)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              margin: 0,
            }}
          >
            <MapPin style={{ color: '#38bdf8' }} /> Cadastral GIS Map
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            Interactive geospatial visualization of verified land parcels, survey boundaries, and discrepancies.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            onClick={loadParcels}
            disabled={isLoading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.5rem 1rem',
              backgroundColor: 'var(--card-bg)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              color: 'var(--text-primary)',
              cursor: 'pointer',
              fontWeight: 500,
              fontSize: '0.875rem',
            }}
          >
            <RefreshCw size={16} className={isLoading ? 'spin' : ''} />
            Refresh Map
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '1rem',
          backgroundColor: 'var(--card-bg)',
          padding: '0.875rem 1.25rem',
          borderRadius: '12px',
          border: '1px solid var(--border-color)',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Filter size={16} style={{ color: '#94a3b8' }} />
          <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-primary)',
              borderRadius: '6px',
              padding: '0.35rem 0.65rem',
              fontSize: '0.85rem',
            }}
          >
            <option value="">All Statuses</option>
            <option value="VALIDATED">Validated (Passed)</option>
            <option value="FLAGGED">Flagged / Needs Review</option>
            <option value="NORMALIZED">Normalized</option>
            <option value="EXTRACTED">Extracted</option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer', fontSize: '0.85rem' }}>
            <input
              type="checkbox"
              checked={discrepancyOnly}
              onChange={(e) => setDiscrepancyOnly(e.target.checked)}
              style={{ accentColor: '#ef4444' }}
            />
            <span style={{ color: discrepancyOnly ? '#f87171' : 'var(--text-secondary)', fontWeight: 500 }}>
              Discrepancies Only
            </span>
          </label>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginLeft: 'auto' }}>
          <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '0.5rem' }}>
            <div style={{ position: 'relative' }}>
              <Search
                size={14}
                style={{
                  position: 'absolute',
                  left: '10px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: '#94a3b8',
                }}
              />
              <input
                type="text"
                placeholder="Filter by village name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  padding: '0.35rem 0.65rem 0.35rem 2rem',
                  borderRadius: '6px',
                  border: '1px solid var(--border-color)',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  fontSize: '0.85rem',
                  width: '200px',
                }}
              />
            </div>
            <button
              type="submit"
              style={{
                padding: '0.35rem 0.75rem',
                backgroundColor: 'rgba(56, 189, 248, 0.15)',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                borderRadius: '6px',
                color: '#38bdf8',
                cursor: 'pointer',
                fontSize: '0.85rem',
                fontWeight: 600,
              }}
            >
              Filter
            </button>
          </form>

          {/* Layer toggles */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', borderLeft: '1px solid var(--border-color)', paddingLeft: '0.75rem' }}>
            <button
              onClick={() => setShowBoundaries(!showBoundaries)}
              title="Toggle Parcel Polygon Boundaries"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem',
                padding: '0.3rem 0.6rem',
                borderRadius: '6px',
                border: '1px solid var(--border-color)',
                backgroundColor: showBoundaries ? 'rgba(16, 185, 129, 0.15)' : 'transparent',
                color: showBoundaries ? '#10b981' : 'var(--text-secondary)',
                fontSize: '0.8rem',
                cursor: 'pointer',
              }}
            >
              <Layers size={14} /> Boundaries
            </button>
            <button
              onClick={() => setShowMarkers(!showMarkers)}
              title="Toggle Pin Markers"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem',
                padding: '0.3rem 0.6rem',
                borderRadius: '6px',
                border: '1px solid var(--border-color)',
                backgroundColor: showMarkers ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
                color: showMarkers ? '#38bdf8' : 'var(--text-secondary)',
                fontSize: '0.8rem',
                cursor: 'pointer',
              }}
            >
              <MapPin size={14} /> Pins
            </button>
          </div>
        </div>
      </div>

      {/* Main Map + Sidebar Split View */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: selectedParcel ? '1fr 360px' : '1fr',
          gap: '1.25rem',
          flex: 1,
          minHeight: '560px',
        }}
      >
        {/* Map Container */}
        <div
          style={{
            position: 'relative',
            borderRadius: '12px',
            overflow: 'hidden',
            border: '1px solid var(--border-color)',
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)',
            backgroundColor: '#0a0d14',
          }}
        >
          {/* Leaflet Mount target */}
          <div ref={mapContainerRef} style={{ width: '100%', height: '100%', minHeight: '560px' }} />

          {/* Loading Overlay */}
          {isLoading && (
            <div
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'rgba(10, 13, 20, 0.6)',
                backdropFilter: 'blur(3px)',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 1000,
                color: '#38bdf8',
                gap: '0.75rem',
              }}
            >
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  border: '3px solid rgba(56, 189, 248, 0.2)',
                  borderTopColor: '#38bdf8',
                  borderRadius: '50%',
                  animation: 'spin 0.8s linear infinite',
                }}
              />
              <span style={{ fontSize: '0.875rem', fontWeight: 600 }}>Loading Cadastral Parcel Coordinates...</span>
            </div>
          )}

          {/* Error Banner */}
          {error && (
            <div
              style={{
                position: 'absolute',
                top: '1rem',
                left: '1rem',
                right: '1rem',
                backgroundColor: 'rgba(239, 68, 68, 0.9)',
                color: '#ffffff',
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                zIndex: 1000,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <AlertTriangle size={18} />
                <span style={{ fontSize: '0.875rem' }}>{error}</span>
              </div>
              <button
                onClick={loadParcels}
                style={{
                  background: 'none',
                  border: '1px solid #ffffff',
                  color: '#ffffff',
                  padding: '0.25rem 0.5rem',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '0.75rem',
                }}
              >
                Retry
              </button>
            </div>
          )}

          {/* Empty State on Map */}
          {!isLoading && !error && parcels.length === 0 && (
            <div
              style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                backgroundColor: 'rgba(15, 23, 42, 0.95)',
                border: '1px solid var(--border-color)',
                padding: '2rem',
                borderRadius: '12px',
                textAlign: 'center',
                maxWidth: '420px',
                zIndex: 1000,
                boxShadow: '0 8px 30px rgba(0,0,0,0.5)',
              }}
            >
              <Info size={36} style={{ color: '#38bdf8', margin: '0 auto 0.75rem' }} />
              <h3 style={{ margin: '0 0 0.5rem', fontSize: '1.1rem', color: 'var(--text-primary)' }}>
                No Spatial Parcels Located
              </h3>
              <p style={{ margin: '0 0 1.25rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                No land records matching your filters currently contain GIS coordinates or boundary GeoJSON. Records without coordinates remain fully accessible in the Explorer.
              </p>
              <button
                onClick={() => navigate('records')}
                style={{
                  backgroundColor: '#38bdf8',
                  color: '#0f172a',
                  border: 'none',
                  padding: '0.5rem 1rem',
                  borderRadius: '6px',
                  fontWeight: 600,
                  fontSize: '0.875rem',
                  cursor: 'pointer',
                }}
              >
                Open Land Records Explorer
              </button>
            </div>
          )}

          {/* Floating Map Legend */}
          <div
            style={{
              position: 'absolute',
              bottom: '1rem',
              left: '1rem',
              backgroundColor: 'rgba(15, 23, 42, 0.9)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              padding: '0.6rem 0.85rem',
              zIndex: 900,
              fontSize: '0.75rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.35rem',
            }}
          >
            <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.2rem' }}>Parcel Status Legend</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#10b981' }}>
              <span style={{ width: '10px', height: '10px', backgroundColor: '#10b981', borderRadius: '2px' }} />
              Validated / Certified
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#f59e0b' }}>
              <span style={{ width: '10px', height: '10px', backgroundColor: '#f59e0b', borderRadius: '2px' }} />
              Pending Verification
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#ef4444' }}>
              <span style={{ width: '10px', height: '10px', backgroundColor: '#ef4444', borderRadius: '2px' }} />
              Flagged / Discrepant
            </div>
          </div>
        </div>

        {/* Selected Parcel Inspector Side Panel */}
        {selectedParcel && (
          <div
            style={{
              backgroundColor: 'var(--card-bg)',
              border: '1px solid var(--border-color)',
              borderRadius: '12px',
              padding: '1.25rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
              boxShadow: '0 4px 20px rgba(0,0,0,0.2)',
              overflowY: 'auto',
              maxHeight: '650px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#38bdf8', textTransform: 'uppercase' }}>
                  Cadastral Parcel
                </span>
                <h3 style={{ margin: '0.2rem 0 0', fontSize: '1.25rem', color: 'var(--text-primary)' }}>
                  Khasra #{selectedParcel.khasra_number}
                </h3>
              </div>
              <button
                onClick={() => setSelectedParcel(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontSize: '1rem',
                  padding: '0.2rem 0.5rem',
                }}
              >
                ✕
              </button>
            </div>

            {/* Status Badges */}
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <span
                style={{
                  padding: '0.25rem 0.6rem',
                  borderRadius: '6px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  backgroundColor: selectedParcel.status === 'VALIDATED' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                  color: selectedParcel.status === 'VALIDATED' ? '#10b981' : '#f87171',
                }}
              >
                {selectedParcel.status}
              </span>
              <span
                style={{
                  padding: '0.25rem 0.6rem',
                  borderRadius: '6px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  backgroundColor: 'rgba(56, 189, 248, 0.15)',
                  color: '#38bdf8',
                }}
              >
                {selectedParcel.review_status}
              </span>
            </div>

            {/* Discrepancy Alert */}
            {selectedParcel.has_discrepancies ? (
              <div
                style={{
                  backgroundColor: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  padding: '0.75rem',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  color: '#f87171',
                  fontSize: '0.85rem',
                }}
              >
                <AlertTriangle size={18} />
                <span>
                  <strong>{selectedParcel.discrepancy_count} Discrepancy Detected</strong> on this survey record.
                </span>
              </div>
            ) : (
              <div
                style={{
                  backgroundColor: 'rgba(16, 185, 129, 0.1)',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                  padding: '0.75rem',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  color: '#10b981',
                  fontSize: '0.85rem',
                }}
              >
                <CheckCircle2 size={18} />
                <span>Zero cross-record discrepancies detected.</span>
              </div>
            )}

            {/* Spatial & Administrative Attributes */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', fontSize: '0.875rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.4rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Khata No:</span>
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{selectedParcel.khata_number}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.4rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Village:</span>
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{selectedParcel.village}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.4rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Tehsil / District:</span>
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{selectedParcel.tehsil}, {selectedParcel.district}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.4rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>State:</span>
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{selectedParcel.state}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.4rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Area:</span>
                <span style={{ fontWeight: 600, color: '#38bdf8' }}>{selectedParcel.area_in_hectares} Hectares</span>
              </div>
              {selectedParcel.latitude && selectedParcel.longitude && (
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.4rem' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Centroid (Lat/Lon):</span>
                  <span style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--text-primary)' }}>
                    {selectedParcel.latitude.toFixed(5)}, {selectedParcel.longitude.toFixed(5)}
                  </span>
                </div>
              )}
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.4rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Geometry Status:</span>
                <span style={{ fontWeight: 600, color: '#10b981' }}>{selectedParcel.geometry_validation_status}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '0.4rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Map Source:</span>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{selectedParcel.map_source}</span>
              </div>
            </div>

            {/* Action Buttons */}
            <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <button
                onClick={() => handleOpenDetail(selectedParcel.record_id)}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem',
                  padding: '0.65rem 1rem',
                  backgroundColor: '#38bdf8',
                  color: '#0f172a',
                  border: 'none',
                  borderRadius: '8px',
                  fontWeight: 600,
                  fontSize: '0.875rem',
                  cursor: 'pointer',
                  transition: 'background-color 0.2s',
                }}
              >
                <Eye size={16} /> Open Full Record Detail
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
