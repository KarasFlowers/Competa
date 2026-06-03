import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Landing from "./pages/Landing";
import TaskCreate from "./pages/TaskCreate";
import TaskDetail from "./pages/TaskDetail";
import ReportView from "./pages/ReportView";
import TraceView from "./pages/TraceView";
import DemoView from "./pages/DemoView";
import SurveyView from "./pages/SurveyView";
import InterviewView from "./pages/InterviewView";

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Landing />} />
        <Route path="/demos/:scenarioId" element={<DemoView />} />
        <Route path="/tasks/new" element={<TaskCreate />} />
        <Route path="/tasks/:id" element={<TaskDetail />} />
        <Route path="/tasks/:id/report" element={<ReportView />} />
        <Route path="/tasks/:id/traces" element={<TraceView />} />
        <Route path="/tasks/:id/survey" element={<SurveyView />} />
        <Route path="/tasks/:id/interview" element={<InterviewView />} />
      </Route>
    </Routes>
  );
}

export default App;
