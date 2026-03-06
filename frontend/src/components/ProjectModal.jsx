import { useState, useEffect } from "react";
import "../styles/projects.css";

export default function ProjectModal({
  project,    
  leads,       
  onClose,
  onSave,
}) {
  const [name, setName] = useState("");
  const [team_name, setTeamName] = useState("");
  const [leadIds, setLeadIds] = useState([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (project) {
      setName(project.name || "");
      setTeamName(project.team_name || "");
      setLeadIds((project.lead_ids || []).map(Number));
    } else {
      setName("");
      setTeamName("");
      setLeadIds([]);
    }
  }, [project]);

  const handleLeadChange = (e) => {
    const selected = Array.from(
      e.target.selectedOptions,
      option => Number(option.value)
    );
    setLeadIds(selected);
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    if (!team_name.trim().toUpperCase()) return;
    if (!leadIds.length) return alert("Select at least one lead");

    setSaving(true);
    try {
      await onSave({
        name: name.trim(),
        team_name: team_name.trim(),
        lead_ids: leadIds,
        is_active: project ? project.is_active : true,
      });
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <form className="modal-card" onSubmit={submit}>
        <div className="modal-header">
          <h3>{project ? "Edit Project" : "Add Project"}</h3>
          <button
            type="button"
            className="close-btn"
            onClick={onClose}
          >
            ✕
          </button>
        </div>

        {/* Project Name */}
        <label>Project Name</label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Enter project name"
          required
          autoFocus
        />
        {/* Team Name */}
        <label>Team</label>
        <input
          value={team_name}
          onChange={(e) => setTeamName(e.target.value)}
          placeholder="Enter Team name"
          required
          autoFocus
        />

        {/* Leads */}
        <label>Assign Leads</label>
        <select
          multiple
          value={leadIds}
          onChange={handleLeadChange}
          className="multi-select"
        >
          {leads.map(l => (
            <option key={l.lead_id} value={l.lead_id}>
              {l.name} ({l.lead_id})
            </option>
          ))}
        </select>

        <div className="modal-hint">
          Hold Ctrl / Cmd to select multiple leads
        </div>

        {/* Actions */}
        <div className="modal-actions">
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
          >
            Cancel
          </button>

          <button
            type="submit"
            className="primary-btn"
            disabled={saving}
          >
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </form>
    </div>
  );
}
