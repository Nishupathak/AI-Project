import ApiExplorer from "../components/ApiExplorer.jsx";
import Telemetry from "../components/Telemetry.jsx";
import { usePoll } from "../api.js";
import { EMPTY_SYSTEM } from "../utils.js";

export default function Console() {
  const [system] = usePoll("/system", 2500, EMPTY_SYSTEM);
  return (
    <div className="page">
      <Telemetry system={system} />
      <ApiExplorer />
    </div>
  );
}
