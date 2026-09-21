"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { AdminLayout } from "@/components/layout/AdminLayout";
import { adminApi } from "@/api/client";
import { CustomerDetail } from "@/types";
import { 
  ArrowLeft, 
  User, 
  Mail, 
  Phone, 
  MapPin, 
  Calendar, 
  FileText, 
  ShieldCheck, 
  AlertCircle,
  Clock
} from "lucide-react";

export default function CustomerDetailPage() {
  const params = useParams();
  const id = params?.id as string;

  const [customer, setCustomer] = useState<CustomerDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCustomer = async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const data = await adminApi.getCustomer(id);
      setCustomer(data);
    } catch (err: any) {
      setError(err.message || "Failed to load customer details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCustomer();
  }, [id]);

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0
    }).format(val);
  };

  return (
    <AdminLayout>
      <div className="space-y-6 max-w-4xl">
        {/* Back Link */}
        <Link
          href="/customers"
          className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-900 transition-colors font-medium"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Back to Customers Registry</span>
        </Link>

        {loading ? (
          <div className="p-12 bg-white border border-slate-200 rounded-xl text-center text-slate-400 text-xs">
            Loading customer profile...
          </div>
        ) : error || !customer ? (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error || "Customer not found."}</span>
          </div>
        ) : (
          <>
            {/* Customer Banner Card */}
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-slate-900 text-white flex items-center justify-center font-bold text-base font-mono">
                  {customer.full_name ? customer.full_name.slice(0, 2).toUpperCase() : "CU"}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h1 className="text-lg font-bold text-slate-900">
                      {customer.full_name || "Customer User"}
                    </h1>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${
                      customer.onboarding_status === "COMPLETED"
                        ? "bg-emerald-100 text-emerald-800 border-emerald-300"
                        : "bg-amber-100 text-amber-800 border-amber-300"
                    }`}>
                      {customer.onboarding_status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 font-mono mt-0.5">
                    {customer.email} • ID: {customer.id.slice(0, 8)}...
                  </p>
                </div>
              </div>

              <div className="text-right text-xs font-mono text-slate-500 sm:self-center">
                APPLICATIONS: <span className="font-bold text-slate-900">{customer.application_count}</span>
              </div>
            </div>

            {/* Grid Information */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Profile Details */}
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4 text-xs">
                <div className="flex items-center gap-2 pb-3 border-b border-slate-100 text-slate-900 font-bold uppercase tracking-wider font-mono text-[11px]">
                  <User className="h-4 w-4 text-slate-500" />
                  <span>Customer Profile</span>
                </div>

                <div className="space-y-3">
                  <div>
                    <span className="text-slate-400 text-[11px] block font-mono">PRIMARY EMAIL</span>
                    <span className="font-mono text-slate-900">{customer.email}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[11px] block font-mono">PHONE NUMBER</span>
                    <span className="font-mono text-slate-900">{customer.phone_number || "Not on file"}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[11px] block font-mono">PREFERRED LANGUAGE</span>
                    <span className="text-slate-900 font-medium">{customer.language || "English"}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[11px] block font-mono">DATE OF BIRTH</span>
                    <span className="font-mono text-slate-900">{customer.date_of_birth || "Not specified"}</span>
                  </div>
                </div>
              </div>

              {/* Residential / Location Info */}
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4 text-xs">
                <div className="flex items-center gap-2 pb-3 border-b border-slate-100 text-slate-900 font-bold uppercase tracking-wider font-mono text-[11px]">
                  <MapPin className="h-4 w-4 text-slate-500" />
                  <span>Location & Account Info</span>
                </div>

                <div className="space-y-3">
                  <div>
                    <span className="text-slate-400 text-[11px] block font-mono">ADDRESS</span>
                    <span className="text-slate-900">{customer.address || "Not specified"}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[11px] block font-mono">CITY / STATE / PINCODE</span>
                    <span className="text-slate-900">
                      {customer.city || customer.state || customer.pincode
                        ? `${customer.city || ""}${customer.city && customer.state ? ", " : ""}${customer.state || ""} ${customer.pincode || ""}`
                        : "Not specified"}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[11px] block font-mono">REGISTRATION DATE</span>
                    <span className="font-mono text-slate-900">{new Date(customer.created_at).toLocaleString()}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[11px] block font-mono">LAST ACTIVE</span>
                    <span className="font-mono text-slate-900">
                      {customer.last_login_at ? new Date(customer.last_login_at).toLocaleString() : "Never"}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Applications List */}
            <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
              <div className="p-4 border-b border-slate-200 flex items-center justify-between">
                <div className="flex items-center gap-2 font-bold text-xs text-slate-900 uppercase font-mono">
                  <FileText className="h-4 w-4 text-slate-500" />
                  <span>Submitted Loan Applications ({customer.applications.length})</span>
                </div>
              </div>

              {customer.applications.length === 0 ? (
                <div className="p-8 text-center text-slate-400 text-xs">
                  No credit applications initiated by this customer yet.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 text-slate-600 uppercase font-mono text-[11px] tracking-wider border-b border-slate-200">
                      <tr>
                        <th className="px-4 py-3">Reference ID</th>
                        <th className="px-4 py-3">Loan Facility</th>
                        <th className="px-4 py-3">Amount</th>
                        <th className="px-4 py-3">Tenure</th>
                        <th className="px-4 py-3">Status</th>
                        <th className="px-4 py-3 text-right">Submitted</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-mono">
                      {customer.applications.map((app) => (
                        <tr key={app.id} className="hover:bg-slate-50 transition-colors">
                          <td className="px-4 py-3 font-bold text-slate-900">
                            {app.id.slice(0, 8)}...
                          </td>
                          <td className="px-4 py-3 font-sans text-slate-700">
                            {app.loan_type}
                          </td>
                          <td className="px-4 py-3 font-bold text-slate-900">
                            {formatCurrency(app.requested_amount)}
                          </td>
                          <td className="px-4 py-3 text-slate-600 font-sans">
                            {app.tenure} Months
                          </td>
                          <td className="px-4 py-3">
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold border uppercase bg-slate-100 text-slate-800 border-slate-300">
                              {app.status}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right text-slate-500 text-[11px]">
                            {new Date(app.created_at).toLocaleDateString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </AdminLayout>
  );
}
