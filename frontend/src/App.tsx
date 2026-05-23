import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Landing from "./pages/Landing";
import TaskCreate from "./pages/TaskCreate";

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Landing />} />
        <Route path="/tasks/new" element={<TaskCreate />} />
      </Route>
    </Routes>
  );
}

export default App;
