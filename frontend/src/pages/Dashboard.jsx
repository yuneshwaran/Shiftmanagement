import { useAuth } from "../context/AuthContext";
import "../styles/dashboard.css";
import illustration from "../assets/illustration.jpg";

function Dashboard() {
  const { user, selectedProject } = useAuth();

  if (!selectedProject) {
    return <div className="dashboard-empty">No project selected</div>;
  }

  return (
    <div className="dashboard-container">

      {/* HERO SECTION */}
      <div className="dashboard-hero">
        <div className="dashboard-left">
          <h1>
            Welcome <span>{user?.name},</span>
          </h1>

          <p className="dashboard-subtitle">
            ShiftRoster helps leads efficiently plan, review, and manage 
            employee shifts while tracking allowances with complete clarity.
          </p>

          <div className="dashboard-features">
            <div className="feature-card">
              <h3>📅 Smart Shift Planning</h3>
              <p>Create and manage weekly shift allocations effortlessly.</p>
            </div>

            <div className="feature-card">
              <h3>✅ Easy Review Process</h3>
              <p>Approve and validate shift assignments with clarity.</p>
            </div>

            <div className="feature-card">
              <h3>💰 Allowance Tracking</h3>
              <p>Accurate weekend & holiday allowance calculations.</p>
            </div>
          </div>
        </div>

        <div className="dashboard-right">
          <img
            src={illustration}
            alt="Shift planning illustration"
          />
        </div>
      </div>

      {/* ROLE MESSAGE */}
      <div className="dashboard-role-info">
        {user?.user_type === "employee" ? (
          <p>
            As an employee, you can review your assigned shifts and
            track your allowances for each month.
          </p>
        ) : (
          <p>
            As a project lead, you can allocate shifts, review approvals,
            manage resources, and generate allowance reports.
          </p>
        )}
      </div>

    </div>
  );
}

export default Dashboard;