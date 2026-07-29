import { motion } from "framer-motion";
import { User, Calendar, Activity, ClipboardList, AlertCircle, Pill, Stethoscope, MessageSquare } from "lucide-react";
import type { StructuredMedicalData } from "@/lib/mockApi";

interface MedicalReportViewProps {
    data: StructuredMedicalData;
}

export function MedicalReportView({ data }: MedicalReportViewProps) {
    const { patientInfo, testResults, medicines, diagnosis, advice } = data;

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            className="space-y-6 animate-in fade-in duration-500 pb-8"
        >
            {/* Patient Header Card */}
            <div className="bg-card rounded-2xl border border-border shadow-sm overflow-hidden">
                <div className="bg-primary/5 border-b border-border p-4">
                    <div className="flex items-center gap-2">
                        <ClipboardList className="w-5 h-5 text-primary" />
                        <h3 className="font-semibold text-foreground">Patient Information</h3>
                    </div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 p-4">
                    <div className="flex items-center gap-3 p-3 rounded-xl bg-muted/30">
                        <User className="w-4 h-4 text-muted-foreground" />
                        <div>
                            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">Name</p>
                            <p className="text-sm font-semibold truncate max-w-[120px]">{patientInfo.name || "N/A"}</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-3 p-3 rounded-xl bg-muted/30">
                        <Activity className="w-4 h-4 text-muted-foreground" />
                        <div>
                            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">Age / Gender</p>
                            <p className="text-sm font-semibold">{patientInfo.age || "?"}Y / {patientInfo.gender || "NA"}</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-3 p-3 rounded-xl bg-muted/30">
                        <Calendar className="w-4 h-4 text-muted-foreground" />
                        <div>
                            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">Report Date</p>
                            <p className="text-sm font-semibold">{patientInfo.date || "N/A"}</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-3 p-3 rounded-xl bg-muted/30">
                        <AlertCircle className="w-4 h-4 text-muted-foreground" />
                        <div>
                            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">Status</p>
                            <p className="text-sm font-semibold text-emerald-600">Processed</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Diagnosis Section */}
            {diagnosis && (
                <div className="bg-card rounded-2xl border border-border shadow-sm overflow-hidden">
                    <div className="bg-amber-500/5 border-b border-border p-4">
                        <div className="flex items-center gap-2">
                            <Stethoscope className="w-5 h-5 text-amber-500" />
                            <h3 className="font-semibold text-foreground">Diagnosis</h3>
                        </div>
                    </div>
                    <div className="p-4">
                        <p className="text-sm text-foreground leading-relaxed italic">"{diagnosis}"</p>
                    </div>
                </div>
            )}

            {/* Medicines Table */}
            {medicines && medicines.length > 0 && (
                <div className="bg-card rounded-2xl border border-border shadow-sm overflow-hidden">
                    <div className="bg-primary/5 border-b border-border p-4">
                        <div className="flex items-center gap-2">
                            <Pill className="w-5 h-5 text-primary" />
                            <h3 className="font-semibold text-foreground">Prescribed Medicines</h3>
                        </div>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="bg-muted/50 border-b border-border">
                                    <th className="px-4 py-3 text-xs font-bold text-muted-foreground uppercase tracking-wider">Medicine</th>
                                    <th className="px-4 py-3 text-xs font-bold text-muted-foreground uppercase tracking-wider">Dosage</th>
                                    <th className="px-4 py-3 text-xs font-bold text-muted-foreground uppercase tracking-wider">Frequency</th>
                                    <th className="px-4 py-3 text-xs font-bold text-muted-foreground uppercase tracking-wider">Duration</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border">
                                {medicines.map((med, idx) => (
                                    <tr key={idx} className="hover:bg-muted/30 transition-colors">
                                        <td className="px-4 py-3 text-sm font-medium text-foreground">{med.name}</td>
                                        <td className="px-4 py-3 text-sm font-bold text-primary">{med.dosage}</td>
                                        <td className="px-4 py-3 text-sm text-muted-foreground">{med.frequency}</td>
                                        <td className="px-4 py-3 text-sm text-muted-foreground">{med.duration}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Lab Results Table */}
            {testResults && testResults.length > 0 && (
                <div className="bg-card rounded-2xl border border-border shadow-sm overflow-hidden">
                    <div className="bg-primary/5 border-b border-border p-4">
                        <div className="flex items-center gap-2">
                            <Activity className="w-5 h-5 text-primary" />
                            <h3 className="font-semibold text-foreground">Lab Test Results</h3>
                        </div>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="bg-muted/50 border-b border-border">
                                    <th className="px-4 py-3 text-xs font-bold text-muted-foreground uppercase tracking-wider">Parameter</th>
                                    <th className="px-4 py-3 text-xs font-bold text-muted-foreground uppercase tracking-wider">Result</th>
                                    <th className="px-4 py-3 text-xs font-bold text-muted-foreground uppercase tracking-wider">Unit</th>
                                    <th className="px-4 py-3 text-xs font-bold text-muted-foreground uppercase tracking-wider">Reference Range</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border">
                                {testResults.map((result, idx) => (
                                    <tr key={idx} className="hover:bg-muted/30 transition-colors">
                                        <td className="px-4 py-3 text-sm font-medium text-foreground">{result.parameter}</td>
                                        <td className="px-4 py-3 text-sm font-bold text-primary">{result.result}</td>
                                        <td className="px-4 py-3 text-sm text-muted-foreground">{result.unit}</td>
                                        <td className="px-4 py-3 text-sm text-muted-foreground italic">{result.range}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Advice Section */}
            {advice && (
                <div className="bg-card rounded-2xl border border-border shadow-sm overflow-hidden">
                    <div className="bg-blue-500/5 border-b border-border p-4">
                        <div className="flex items-center gap-2">
                            <MessageSquare className="w-5 h-5 text-blue-500" />
                            <h3 className="font-semibold text-foreground">Doctor's Advice</h3>
                        </div>
                    </div>
                    <div className="p-4">
                        <p className="text-sm text-foreground leading-relaxed">{advice}</p>
                    </div>
                </div>
            )}
        </motion.div>
    );
}
