import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { api, ApiError } from "../../api/client";
import type { Building, Unit, UnitKind, VisitorParkingSpot } from "../../api/types";
import { ErrorMessage } from "../../components/ErrorMessage";
import { useApiData } from "../../hooks/useApiData";

export function UnitsAdminPage() {
  const { t } = useTranslation();
  const buildings = useApiData<Building[]>("/buildings");
  const units = useApiData<Unit[]>("/units");
  const spots = useApiData<VisitorParkingSpot[]>("/visitor-parking-spots");
  const [buildingName, setBuildingName] = useState("");
  const [kind, setKind] = useState<UnitKind>("house");
  const [buildingId, setBuildingId] = useState("");
  const [floor, setFloor] = useState("");
  const [number, setNumber] = useState("");
  const [spotNumber, setSpotNumber] = useState("");
  const [actionError, setActionError] = useState<ApiError | null>(null);

  const buildingName_ = (id: number | null) =>
    buildings.data?.find((b) => b.id === id)?.name ?? "—";

  async function run(action: () => Promise<unknown>, after: () => void) {
    setActionError(null);
    try {
      await action();
      after();
    } catch (error) {
      if (error instanceof ApiError) setActionError(error);
    }
  }

  function createBuilding(event: FormEvent) {
    event.preventDefault();
    void run(
      () =>
        api("/buildings", {
          method: "POST",
          body: JSON.stringify({ name: buildingName }),
        }),
      () => {
        setBuildingName("");
        buildings.reload();
      },
    );
  }

  function createUnit(event: FormEvent) {
    event.preventDefault();
    const payload =
      kind === "apartment"
        ? { kind, number, building_id: Number(buildingId), floor: Number(floor) }
        : { kind, number };
    void run(
      () => api("/units", { method: "POST", body: JSON.stringify(payload) }),
      () => {
        setNumber("");
        units.reload();
      },
    );
  }

  function createSpot(event: FormEvent) {
    event.preventDefault();
    void run(
      () =>
        api("/visitor-parking-spots", {
          method: "POST",
          body: JSON.stringify({ number: spotNumber }),
        }),
      () => {
        setSpotNumber("");
        spots.reload();
      },
    );
  }

  return (
    <section>
      <h2>{t("nav.units")}</h2>

      <h3>{t("unitsAdmin.buildings")}</h3>
      <ul className="chips">
        {buildings.data?.map((building) => (
          <li key={building.id}>{building.name}</li>
        ))}
      </ul>
      <form onSubmit={createBuilding} className="inline-form">
        <label htmlFor="building-name">{t("unitsAdmin.newBuilding")}</label>
        <input
          id="building-name"
          required
          value={buildingName}
          onChange={(event) => setBuildingName(event.target.value)}
        />
        <button type="submit">{t("common.create")}</button>
      </form>

      <h3>{t("unitsAdmin.units")}</h3>
      {units.data !== null && (
        <table>
          <thead>
            <tr>
              <th>{t("unit.number")}</th>
              <th>{t("unit.kind")}</th>
              <th>{t("unit.building")}</th>
              <th>{t("unit.floor")}</th>
              <th>{t("common.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {units.data.map((unit) => (
              <tr key={unit.id}>
                <td>{unit.number}</td>
                <td>{t(`unit.kinds.${unit.kind}`)}</td>
                <td>{buildingName_(unit.building_id)}</td>
                <td>{unit.floor ?? "—"}</td>
                <td>
                  <Link to={`/units/${unit.id}`}>{t("common.open")}</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <form onSubmit={createUnit} className="stack-form">
        <h4>{t("unitsAdmin.newUnit")}</h4>
        <label htmlFor="unit-kind">{t("unit.kind")}</label>
        <select
          id="unit-kind"
          value={kind}
          onChange={(event) => setKind(event.target.value as UnitKind)}
        >
          <option value="house">{t("unit.kinds.house")}</option>
          <option value="apartment">{t("unit.kinds.apartment")}</option>
        </select>
        {kind === "apartment" && (
          <>
            <label htmlFor="unit-building">{t("unit.building")}</label>
            <select
              id="unit-building"
              required
              value={buildingId}
              onChange={(event) => setBuildingId(event.target.value)}
            >
              <option value="" />
              {buildings.data?.map((building) => (
                <option key={building.id} value={building.id}>
                  {building.name}
                </option>
              ))}
            </select>
            <label htmlFor="unit-floor">{t("unit.floor")}</label>
            <input
              id="unit-floor"
              type="number"
              required
              value={floor}
              onChange={(event) => setFloor(event.target.value)}
            />
          </>
        )}
        <label htmlFor="unit-number">{t("unit.number")}</label>
        <input
          id="unit-number"
          required
          value={number}
          onChange={(event) => setNumber(event.target.value)}
        />
        <button type="submit">{t("common.create")}</button>
      </form>

      <h3>{t("unitsAdmin.visitorSpots")}</h3>
      <ul className="chips">
        {spots.data?.map((spot) => (
          <li key={spot.id}>{spot.number}</li>
        ))}
      </ul>
      <form onSubmit={createSpot} className="inline-form">
        <label htmlFor="spot-number">{t("unitsAdmin.spotNumber")}</label>
        <input
          id="spot-number"
          required
          value={spotNumber}
          onChange={(event) => setSpotNumber(event.target.value)}
        />
        <button type="submit">{t("common.create")}</button>
      </form>
      <ErrorMessage error={actionError} />
    </section>
  );
}
