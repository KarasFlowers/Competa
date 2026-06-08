import { Outlet, Link, NavLink } from "react-router-dom";
import { BarChart3 } from "lucide-react";

function navClassName(isActive: boolean) {
  return [
    "text-sm font-medium transition-colors",
    isActive ? "text-blue-700" : "text-gray-600 hover:text-gray-900",
  ].join(" ");
}

export default function Layout() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link to="/" className="flex items-center gap-2 text-xl font-bold text-gray-900">
              <BarChart3 className="w-6 h-6 text-blue-600" />
              Competa
            </Link>
            <nav className="flex items-center gap-6">
              <NavLink
                to="/"
                end
                className={({ isActive }) => navClassName(isActive)}
              >
                首页
              </NavLink>
              <NavLink
                to="/tasks"
                className={({ isActive }) => navClassName(isActive)}
              >
                任务工作台
              </NavLink>
              <Link
                to="/tasks/new"
                className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
              >
                新建分析
              </Link>
            </nav>
          </div>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}
