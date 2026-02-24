import api from "./axios";

export const getAssignedEmployees = (projectId) => {
  return api.get(`/assignments/projects/${projectId}/employees`);
};

export const getAvailableEmployees = (projectId) => {
  return api.get(
    `/assignments/projects/${projectId}/employees/available`
  );
};

export const assignEmployee = (projectId, empId) => {
  return api.post(
    `/assignments/projects/${projectId}/employees/${empId}`
  );
};



export const removeEmployee = (projectId, empId) => {
  return api.delete(
    `/assignments/projects/${projectId}/employees/${empId}`
  );
};
