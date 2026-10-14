import VisionPanel from "../components/VisionPanel.jsx";
import SignalsPanel from "../components/SignalsPanel.jsx";
import IdentityPanel from "../components/IdentityPanel.jsx";
import VoicePanel from "../components/VoicePanel.jsx";
import ChatPanel from "../components/ChatPanel.jsx";

export default function Dashboard() {
  return (
    <div className="dash">
      <div className="col">
        <VisionPanel />
        <div className="row2">
          <SignalsPanel />
          <IdentityPanel />
        </div>
      </div>
      <div className="col">
        <VoicePanel />
        <ChatPanel />
      </div>
    </div>
  );
}
