import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { getDetailedAllowanceReport, getReportEmployees } from "../api/allowance.api";
import { getProjects } from "../api/projects.api";
import { getLastDayOfMonth } from "../utils/date";
import "../styles/analysis.css";

export default function AllowanceAnalysis() {

  const navigate = useNavigate();

  const [filterType, setFilterType] = useState("project"); 
  const [selectionId, setSelectionId] = useState(null);

  const [projects, setProjects] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [month, setMonth] = useState("2025-01");
  const [summary, setSummary] = useState(null);
  const [daily, setDaily] = useState([]);
  const [loading, setLoading] = useState(false);

  const formattedMonth = month
    ? new Date(month + "-01").toLocaleString("default", {
        month: "long",
        year: "numeric",
      })
    : "";

  const selectedName = (() => {
    if (!selectionId) {
      return filterType === "project"
        ? "All Projects"
        : "All Employees";
    }

    if (filterType === "project") {
      return projects.find(p => p.project_id === selectionId)?.name;
    }

    return employees.find(e => e.emp_id === selectionId)?.emp_name;
  })();

  const pageTitle = `Allowance Analysis – ${selectedName} (${formattedMonth})`;

  useEffect(() => {
    loadOptions();
    setSelectionId(null); 
  }, [filterType]);

  const loadOptions = async () => {
    try {
      if (filterType === "project") {
        const res = await getProjects(); 
        setProjects(res.data || []);
      } else {
        const res = await getReportEmployees();
        setEmployees(res.data || []);
      }
    } catch (err) {
      console.error("Failed to load filter options", err);
    }
  };
  useEffect(() => {
    loadEmployees();
  }, []);

  const loadEmployees = async () => {
    try {
      const res = await getReportEmployees();  
      setEmployees(res.data || []);
    } catch (err) {
      console.error("Failed to load employees", err);
    }
  };

const handleAnalyze = async () => {
  if (!month) return;

  const [year, mon] = month.split("-");
  const lastDay = getLastDayOfMonth(Number(year), Number(mon));

  const fromDate = `${year}-${mon}-01`;
  const toDate = `${year}-${mon}-${lastDay}`;

  try {
    setLoading(true);

    const res = await getDetailedAllowanceReport({
      projectId: filterType === "project" ? selectionId : null,
      empId: filterType === "employee" ? selectionId : null,
      fromDate,
      toDate,
    });

    setSummary(res?.data?.summary || null);
    setDaily(res?.data?.daily || []);

  } catch (err) {
    console.error("Detailed allowance error:", err);
    setSummary(null);
    setDaily([]);
  } finally {
    setLoading(false);
  }
};

  return (
    <div className="report-container">
      
    <div className="analysis-filters">

      {/* Filter Type */}
      <div className="filter-group">
        <label>Filter By</label>
        <select
          value={filterType}
          onChange={e => setFilterType(e.target.value)}
        >
          <option value="project">Project</option>
          <option value="employee">Employee</option>
        </select>
      </div>

      {/* Dynamic Selection */}
      <div className="filter-group">
        <label>
          {filterType === "project" ? "Project" : "Employee"}
        </label>

        <select
          value={selectionId || ""}
          onChange={e =>
            setSelectionId(e.target.value ? Number(e.target.value) : null)
          }
        >
          <option value="">
            {filterType === "project"
              ? "All Projects"
              : "All Employees"}
          </option>

          {(filterType === "project" ? projects : employees).map(item => (
            <option
              key={
                filterType === "project"
                  ? item.project_id
                  : item.emp_id
              }
              value={
                filterType === "project"
                  ? item.project_id
                  : item.emp_id
              }
            >
              {filterType === "project"
                ? item.name
                : item.emp_name}
            </option>
          ))}
        </select>
      </div>

      {/* Month */}
      <div className="filter-group">
        <label>Month</label>
        <input
          type="month"
          value={month}
          onChange={e => setMonth(e.target.value)}
        />
      </div>

      {/* Buttons */}
      <div className="filter-actions">
        <button className="primary-btn" onClick={handleAnalyze}>
          Analyze
        </button>

        <button
          className="secondary-btn"
          onClick={() => navigate("/home/report")}
        >
          ← Back to Summary
        </button>
      </div>

    </div>
      {summary && <div className="analysis-header">
              <h2 className="analysis-title">{pageTitle}</h2>
      </div>
      }
      {loading && <div className="empty-state">Loading...</div>}

      {summary && (
        <div className="analysis-stats">

          <div className="stat-card">
            <span className="stat-label">Weekday Shifts</span>
            <span className="stat-value">{summary.weekday_count}</span>
          </div>

          <div className="stat-card">
            <span className="stat-label">Weekend Shifts</span>
            <span className="stat-value">{summary.weekend_count}</span>
          </div>

          <div className="stat-card">
            <span className="stat-label">Holiday Shifts</span>
            <span className="stat-value">{summary.holiday_count}</span>
          </div>

          <div className="stat-card highlight">
            <span className="stat-label">Total Allowance</span>
            <span className="stat-value">
              ₹ {Number(summary.total_allowance).toFixed(2)}
            </span>
          </div>

        </div>
      )}

      {daily.length > 0 && (
        <table className="report-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Project</th>
              <th>Shift</th>
              <th>Type</th>
              <th>Allowance</th>
            </tr>
          </thead>

          <tbody>
            {daily.map((d, idx) => (
              <tr key={idx}>
                <td>{d.date}</td>
                <td>{d.project}</td>
                <td>{d.shift_code}</td>
                <td>{d.type}</td>
                <td>₹ {Number(d.allowance).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

    </div>
  );
}