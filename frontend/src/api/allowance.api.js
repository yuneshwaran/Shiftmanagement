import api from "./axios";

export const getAllowanceReport = ({
  projectId,
  fromDate,
  toDate,
}) => {
  const endpoint = projectId
    ? "/allowances/reports/employee-allowance"
    : "/allowances/reports/employee-allowance/aggregate";

  return api.get(endpoint, {
    params: projectId
      ? {
          project_id: projectId,
          from_date: fromDate,
          to_date: toDate,
        }
      : {
          from_date: fromDate,
          to_date: toDate,
        },
  });
};


export const getDetailedAllowanceReport = ({
  projectId,
  empId,
  fromDate,
  toDate,
}) =>
  api.get("/allowances/reports/employee-allowance/detailed", {
    params: {
      project_id: projectId || undefined,
      emp_id: empId || undefined,
      from_date: fromDate,
      to_date: toDate,
    },
  });

  export const getReportEmployees = (projectId) =>
  api.get("/allowances/reports/employees", {
    params: {
      project_id: projectId || undefined,
    },
  });