import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { api, ApiError } from "../../api/client";
import type { ParkingSpot, Vehicle } from "../../api/types";
import { useApiData } from "../../hooks/useApiData";
import { ErrorMessage } from "../ErrorMessage";

export function VehiclesTab({ unitId }: { unitId: number }) {
  const { t } = useTranslation();
  const spots = useApiData<ParkingSpot[]>(`/units/${unitId}/parking-spots`);
  const vehicles = useApiData<Vehicle[]>(`/units/${unitId}/vehicles`);
  const [plate, setPlate] = useState("");
  const [description, setDescription] = useState("");
  const [actionError, setActionError] = useState<ApiError | null>(null);

  if (vehicles.error) return <ErrorMessage error={vehicles.error} />;
  if (vehicles.data === null) return <p className="status">{t("common.loading")}</p>;

  async function addVehicle(event: FormEvent) {
    event.preventDefault();
    setActionError(null);
    try {
      await api(`/units/${unitId}/vehicles`, {
        method: "POST",
        body: JSON.stringify({ plate, description: description || null }),
      });
      setPlate("");
      setDescription("");
      vehicles.reload();
    } catch (error) {
      if (error instanceof ApiError) setActionError(error);
    }
  }

  async function removeVehicle(vehicleId: number) {
    setActionError(null);
    try {
      await api(`/units/${unitId}/vehicles/${vehicleId}`, { method: "DELETE" });
      vehicles.reload();
    } catch (error) {
      if (error instanceof ApiError) setActionError(error);
    }
  }

  return (
    <div>
      <h4>{t("vehicles.parkingSpots")}</h4>
      {spots.data !== null &&
        (spots.data.length === 0 ? (
          <p className="hint">{t("vehicles.noSpots")}</p>
        ) : (
          <ul className="chips">
            {spots.data.map((spot) => (
              <li key={spot.id}>{spot.number}</li>
            ))}
          </ul>
        ))}

      {vehicles.data.length === 0 ? (
        <p className="hint">{t("vehicles.noVehicles")}</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>{t("vehicles.plate")}</th>
              <th>{t("vehicles.description")}</th>
              <th>{t("common.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {vehicles.data.map((vehicle) => (
              <tr key={vehicle.id}>
                <td>{vehicle.plate}</td>
                <td>{vehicle.description ?? "—"}</td>
                <td>
                  <button
                    type="button"
                    className="ghost"
                    onClick={() => void removeVehicle(vehicle.id)}
                  >
                    {t("common.delete")}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <form onSubmit={addVehicle} className="inline-form">
        <label htmlFor="vehicle-plate">{t("vehicles.plate")}</label>
        <input
          id="vehicle-plate"
          required
          value={plate}
          onChange={(event) => setPlate(event.target.value)}
        />
        <label htmlFor="vehicle-description">{t("vehicles.description")}</label>
        <input
          id="vehicle-description"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
        />
        <button type="submit">{t("vehicles.add")}</button>
      </form>
      <ErrorMessage error={actionError} />
    </div>
  );
}
