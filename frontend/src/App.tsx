import { Suspense, lazy, type ReactNode } from "react";
import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";

const Landing = lazy(() => import("./pages/Landing"));
const TaskCreate = lazy(() => import("./pages/TaskCreate"));
const TaskDetail = lazy(() => import("./pages/TaskDetail"));
const TasksWorkspace = lazy(() => import("./pages/TasksWorkspace"));
const ReportView = lazy(() => import("./pages/ReportView"));
const TraceView = lazy(() => import("./pages/TraceView"));
const DemoView = lazy(() => import("./pages/DemoView"));
const SurveyView = lazy(() => import("./pages/SurveyView"));
const InterviewView = lazy(() => import("./pages/InterviewView"));

function RouteFallback() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <div className="rounded-2xl border border-gray-200 bg-white px-6 py-4 text-sm text-gray-500 shadow-sm">
        页面加载中...
      </div>
    </div>
  );
}

function withSuspense(element: ReactNode) {
  return <Suspense fallback={<RouteFallback />}>{element}</Suspense>;
}

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={withSuspense(<Landing />)} />
        <Route path="/demos/:scenarioId" element={withSuspense(<DemoView />)} />
        <Route path="/tasks" element={withSuspense(<TasksWorkspace />)} />
        <Route path="/tasks/new" element={withSuspense(<TaskCreate />)} />
        <Route path="/tasks/:id" element={withSuspense(<TaskDetail />)} />
        <Route path="/tasks/:id/report" element={withSuspense(<ReportView />)} />
        <Route path="/tasks/:id/traces" element={withSuspense(<TraceView />)} />
        <Route path="/tasks/:id/survey" element={withSuspense(<SurveyView />)} />
        <Route path="/tasks/:id/interview" element={withSuspense(<InterviewView />)} />
      </Route>
    </Routes>
  );
}

export default App;
