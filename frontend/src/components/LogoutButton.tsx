import React from "react";
import { useAuth } from "@/contexts/AuthContext";
import { LogOut } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { cn } from "@/lib/utils";
import { Tooltip } from "@/components/ui/Tooltip";

interface LogoutButtonProps {
  className?: string;
  showIcon?: boolean;
  children?: React.ReactNode;
}

export function LogoutButton({ className, showIcon = true, children }: LogoutButtonProps) {
  const { logout } = useAuth();

  const handleConfirm = () => {
    logout();
  };

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <button className={cn("flex items-center gap-2", className)}>
          {/* Wrap only the icon button with tooltip if children is empty, or wrap the whole button */}
          <Tooltip 
            title="Sign Out" 
            description="Securely end your session."
            placement="bottom"
            disabled={!!children}
          >
            <div className="flex items-center gap-2">
              {showIcon && <LogOut className="w-4 h-4" />}
              {children}
            </div>
          </Tooltip>
        </button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Sign Out</AlertDialogTitle>
          <AlertDialogDescription>
            Are you sure you want to log out of your account?
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={handleConfirm} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
            Yes, log out
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
