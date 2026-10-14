import { createContext, useContext } from "react";

// The live robot state (polled once in App and shared with every component).
export const RobotContext = createContext({ status: {}, online: true });
export const useRobot = () => useContext(RobotContext);
