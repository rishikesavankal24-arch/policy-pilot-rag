"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { AdminLayout } from "@/components/layout/AdminLayout";
import { adminApi } from "@/api/client";
import { EmployeeRequestItem } from "@/types";
import { 
  ArrowLeft, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  Building2, 
  User, 
  Mail, 
  Briefcase, 
  AlertCircle,
  HelpCircle,
  ShieldCheck
} from "lucide-react";

export default function EmployeeVerificationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;

  const [request, setRequest] = useState<EmployeeRequestItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Modals
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [showInfoModal, setShowInfoModal] = useState(false);
  const [infoNote, setInfoNote] = useState("");

  const fetchRequest = async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const data = await adminApi.getEmployeeRequest(id);
      setRequest(data);
    } catch (err: any) {
      setError(err.message || "Failed to load request details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequest();
  }, [id]);

  const handleApprove = async () => {
    if (!confirm("Are you sure you want to approve this employee registration? This will grant operational employee privileges to the user.")) return;
    setActionLoading(true);
    try {
      await adminApi.approveEmployeeRequest(id);
      await fetchRequest();
    } catch (err: any) {
      alert(err.message || "Failed to approve request.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rejectReason.trim()) return;
    setActionLoading(true);
    try {
      await adminApi.rejectEmployeeRequest(id, rejectReason.trim());
      setShowRejectModal(false);
      setRejectReason("");
      await fetchRequest();
    } catch (err: any) {
      alert(err.message || "Failed to reject request.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleRequestInfo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!infoNote.trim()) return;
    setActionLoading(true);
    try {
      await adminApi.requestInfo(id, infoNote.trim());
      setShowInfoModal(false);
      setInfoNote("");
      await fetchRequest();
    } catch (err: any) {
      alert(err.message || "Failed to submit admin note.");
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <AdminLayout>
      <div className="space-y-6 max-w-4xl mx-auto">
        
        {/* Navigation Breadcrumb */}
        <div className="flex items-center gap-3">
          <Link
            href="/employee-verification"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold border border-slate-300 transition-colors shadow-xs"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Back to Requests</span>
          </Link>
          <span className="text-slate-400">/</span>
          <span className="text-xs font-mono text-slate-500">
            Request #{id ? id.slice(0, 8) : ""}
          </span>
        </div>

        {/* Loading Spinner */}
        {loading && (
          <div className="p-16 text-center text-slate-500 text-xs">
            <div className="w-8 h-8 border-2 border-slate-900 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
            <span>Loading request details...</span>
          </div>
        )}

        {/* Error Notice */}
        {error && (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs">
            {error}
          </div>
        )}

        {request && !loading && (
          <div className="space-y-6">
            
            {/* Header Banner */}
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2.5">
                  <h1 className="text-xl font-bold text-slate-900">
                    {request.full_name || request.email}
                  </h1>
                  <span className={`px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${
                    request.status === "APPROVED" ? "bg-emerald-100 text-emerald-800 border-emerald-300" :
                    request.status === "REJECTED" ? "bg-rose-100 text-rose-800 border-rose-300" :
                    "bg-amber-100 text-amber-800 border-amber-300"
                  }`}>
                    {request.status}
                  </span>
                </div>
                <p className="text-xs text-slate-500 font-mono mt-1">
                  CASE ID: {request.id} • SUBMITTED: {new Date(request.created_at).toLocaleString()}
                </p>
              </div>

              {/* Action Buttons if PENDING */}
              {request.status === "PENDING" && (
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={handleApprove}
                    disabled={actionLoading}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-lg text-xs flex items-center gap-1.5 transition-colors shadow-xs disabled:opacity-50"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    <span>Approve Employee</span>
                  </button>

                  <button
                    onClick={() => setShowRejectModal(true)}
                    disabled={actionLoading}
                    className="px-3 py-2 bg-rose-600 hover:bg-rose-700 text-white font-semibold rounded-lg text-xs flex items-center gap-1.5 transition-colors shadow-xs disabled:opacity-50"
                  >
                    <XCircle className="h-4 w-4" />
                    <span>Reject</span>
                  </button>

                  <button
                    onClick={() => setShowInfoModal(true)}
                    disabled={actionLoading}
                    className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-lg text-xs flex items-center gap-1.5 transition-colors border border-slate-300 shadow-xs disabled:opacity-50"
                  >
                    <HelpCircle className="h-4 w-4" />
                    <span>Add Note</span>
                  </button>
                </div>
              )}
            </div>

            {/* Applicant & Institutional Details Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4">
                <div className="flex items-center gap-2 pb-3 border-b border-slate-100 text-slate-900 font-semibold text-xs uppercase tracking-wider">
                  <User className="h-4 w-4 text-amber-600" />
                  <span>Applicant Personal Profile</span>
                </div>
                <div className="grid grid-cols-2 gap-y-3 gap-x-4 text-xs">
                  <div>
                    <span className="text-[10px] font-mono uppercase text-slate-400 block">Full Name</span>
                    <span className="font-semibold text-slate-800">{request.full_name || "N/A"}</span>
                  </div>
                  <div>
                    <span className="text-[10px] font-mono uppercase text-slate-400 block">System Email</span>
                    <span className="font-mono text-slate-700 truncate block">{request.email}</span>
                  </div>
                  <div>
                    <span className="text-[10px] font-mono uppercase text-slate-400 block">Work Email</span>
                    <span className="font-mono text-slate-700 truncate block">{request.work_email || "N/A"}</span>
                  </div>
                  <div>
                    <span className="text-[10px] font-mono uppercase text-slate-400 block">Phone Number</span>
                    <span className="text-slate-700">{request.phone_number || "N/A"}</span>
                  </div>
                </div>
              </div>

              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4">
                <div className="flex items-center gap-2 pb-3 border-b border-slate-100 text-slate-900 font-semibold text-xs uppercase tracking-wider">
                  <Building2 className="h-4 w-4 text-amber-600" />
                  <span>Institutional Credential Claims</span>
                </div>
                <div className="grid grid-cols-2 gap-y-3 gap-x-4 text-xs">
                  <div>
                    <span className="text-[10px] font-mono uppercase text-slate-400 block">Organization</span>
                    <span className="font-semibold text-slate-800">{request.organization}</span>
                  </div>
                  <div>
                    <span className="text-[10px] font-mono uppercase text-slate-400 block">Department</span>
                    <span className="text-slate-700">{request.department || "N/A"}</span>
                  </div>
                  <div>
                    <span className="text-[10px] font-mono uppercase text-slate-400 block">Designation</span>
                    <span className="text-slate-700">{request.designation || "N/A"}</span>
                  </div>
                  <div>
                    <span className="text-[10px] font-mono uppercase text-slate-400 block">Employee ID</span>
                    <span className="font-mono font-semibold text-slate-800">{request.employee_id || "N/A"}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Justification & Notes */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-3">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 font-mono">
                Access Request Reason / Notes
              </span>
              <p className="text-xs text-slate-700 bg-slate-50 p-4 rounded-lg border border-slate-100 leading-relaxed">
                {request.reason || "No access reason specified by applicant."}
              </p>

              {request.admin_note && (
                <div className="pt-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-blue-700 font-mono">
                    Supervisory Administrative Note:
                  </span>
                  <p className="text-xs text-blue-900 bg-blue-50 p-3 rounded-lg border border-blue-100 mt-1">
                    {request.admin_note}
                  </p>
                </div>
              )}

              {request.rejection_reason && (
                <div className="pt-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-rose-700 font-mono">
                    Rejection Reason:
                  </span>
                  <p className="text-xs text-rose-900 bg-rose-50 p-3 rounded-lg border border-rose-100 mt-1">
                    {request.rejection_reason}
                  </p>
                </div>
              )}
            </div>

          </div>
        )}

        {/* Reject Modal */}
        {showRejectModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
            <div className="bg-white rounded-2xl border border-slate-200 max-w-md w-full p-6 space-y-4 shadow-2xl">
              <h3 className="text-base font-bold text-slate-900">Reject Employee Request</h3>
              <p className="text-xs text-slate-500">
                Please provide a reason for rejecting this verification request. The applicant will be notified.
              </p>
              <form onSubmit={handleReject} className="space-y-4">
                <textarea
                  required
                  rows={3}
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="e.g. Employee ID could not be validated against directory..."
                  className="w-full p-3 bg-slate-50 border border-slate-300 rounded-lg text-xs focus:outline-none focus:border-rose-500"
                ></textarea>
                <div className="flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowRejectModal(false)}
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={actionLoading}
                    className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-lg disabled:opacity-50"
                  >
                    Confirm Rejection
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Request Info Modal */}
        {showInfoModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
            <div className="bg-white rounded-2xl border border-slate-200 max-w-md w-full p-6 space-y-4 shadow-2xl">
              <h3 className="text-base font-bold text-slate-900">Add Supervisory Note</h3>
              <p className="text-xs text-slate-500">
                Record an internal administrative inquiry note for this applicant.
              </p>
              <form onSubmit={handleRequestInfo} className="space-y-4">
                <textarea
                  required
                  rows={3}
                  value={infoNote}
                  onChange={(e) => setInfoNote(e.target.value)}
                  placeholder="e.g. Pending confirmation from department supervisor..."
                  className="w-full p-3 bg-slate-50 border border-slate-300 rounded-lg text-xs focus:outline-none focus:border-amber-500"
                ></textarea>
                <div className="flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowInfoModal(false)}
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={actionLoading}
                    className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold rounded-lg disabled:opacity-50"
                  >
                    Save Note
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

      </div>
    </AdminLayout>
  );
}
