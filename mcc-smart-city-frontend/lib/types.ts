export type Permission = { id:number; name:string; code:string; description?:string|null; is_active:boolean; is_system:boolean; created_at:string }
export type Role = { id:number; name:string; description?:string|null; is_system:boolean; is_active:boolean; permissions:Permission[]; created_at:string; updated_at:string }
export type Department = { id:number; name:string; code:string; description?:string|null; is_active:boolean; created_at:string; updated_at:string }
export type User = { id:number; full_name:string; employee_number?:string|null; email:string; phone_number?:string|null; department_id?:number|null; role_id?:number|null; status:"active"|"suspended"|"deactivated"; is_active:boolean; is_superuser:boolean; must_change_password:boolean; department?:Department|null; role?:Role|null; created_at:string; updated_at:string }
export type NavigationItem = { id:number; label:string; href:string; icon:string; section:string; sort_order:number; permission_code?:string|null; is_active:boolean; is_system:boolean; created_at:string }
export type LoginResponse = { access_token:string; token_type:string; user:User }
