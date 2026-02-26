import { BrowserRouter, Routes, Route, Navigate } from "react-router";
import { useAuth } from "./context/AuthContext";
import { ToastContainer } from "react-toastify";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import ShiftAllocate from "./pages/ShiftAllocate";
import AppLayout from "./components/AppLayout";
import ShiftReview from "./pages/ShiftReview";
import AllowanceReport from "./pages/AllowanceReport";
import Manage from "./components/Manage";
import AllowanceAnalysis from "./pages/AllowanceAnalysis";

function ProtectedRoute({ children, allowedRoles, adminOnly }) {
  const { user, loading, isAuthenticated } = useAuth();

  if (loading) return null;

  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  if (allowedRoles) {
    if (!user) return null;
    if (!allowedRoles.includes(user.user_type)) {
      return <Navigate to="/home" replace />;
    }
  }

  if (adminOnly) {
    if (!user) return null;
    if (!user.is_admin) {
      return <Navigate to="/home" replace />;
    }
  }

  return children;
}


export default function App() {
  return (
    <BrowserRouter>
      <ToastContainer />

      <Routes>
        
        <Route path="/" element={<Login />} />

        <Route
          path="/home"
          element={
            <ProtectedRoute allowedRoles={["lead", "employee"]}>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Dashboard />} />

          <Route
            path="allocate"
            element={
              <ProtectedRoute allowedRoles={["lead"]}>
                <ShiftAllocate />
              </ProtectedRoute>
            }
          />

          <Route
            path="review"
            element={
              <ProtectedRoute allowedRoles={["lead", "employee"]}>
                <ShiftReview />
              </ProtectedRoute>
            }
          />

          <Route
            path="manage"
            element={
              <ProtectedRoute allowedRoles={["lead"]}>
                <Manage />
              </ProtectedRoute>
            }
          />

          <Route
            path="report"
            element={
              <ProtectedRoute allowedRoles={["lead"]}>
                <AllowanceReport />
              </ProtectedRoute>
            }
          />
          
          <Route
          path="analysis"
          element={
            <ProtectedRoute allowedRoles={["lead"]}>
              <AllowanceAnalysis />
            </ProtectedRoute> 
          }/>
        </Route>

        
       

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
