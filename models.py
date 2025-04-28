from datetime import datetime
import enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr

# Fuel Management Models
class FuelEntry(BaseModel):
    tank_id: str
    shift: str
    litres_received: float
    dip_before: float
    dip_after: float
    attendant: str
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)

class FuelEntryInDB(FuelEntry):
    id: int

class FuelDip(BaseModel):
    tank_id: str
    dip_reading: float
    attendant: str
    shift: str
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)

class FuelDipInDB(FuelDip):
    id: int

class Tank(BaseModel):
    id: str
    fuel_type: str
    capacity: float
    current_level: float
    status: str
    branch_id: str

class TankInDB(Tank):
    id: str

# Sales Management Models
class SaleEntry(BaseModel):
    pump_id: str
    fuel_type: str
    litres_sold: float
    unit_price: float
    attendant: str
    vehicle_number: Optional[str] = None
    payment_method: str
    shift: str
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)

class SaleEntryInDB(SaleEntry):
    id: int
    total_amount: float

class LoyaltyPoints(BaseModel):
    vehicle_number: str
    points: int
    last_updated: datetime

class LoyaltyPointsInDB(LoyaltyPoints):
    id: int

# Staff Management Models
class Attendant(BaseModel):
    name: str
    employee_id: str
    role: str = "pumpman"  # pumpman, manager, senior_manager
    active: bool = True
    branch_id: Optional[str] = None
    contact_number: Optional[str] = None
    join_date: Optional[datetime] = None

class AttendantInDB(Attendant):
    id: int

class Attendance(BaseModel):
    employee_id: str
    check_in: datetime
    check_out: Optional[datetime] = None
    shift: str

class AttendanceInDB(Attendance):
    id: int

class Expense(BaseModel):
    description: str
    amount: float
    category: str
    employee_id: str
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)

class ExpenseInDB(Expense):
    id: int

# Report Models
class ReportRequest(BaseModel):
    report_type: str
    start_date: datetime
    end_date: datetime
    tanks: Optional[List[str]] = None
    employees: Optional[List[str]] = None

class AIReportRequest(ReportRequest):
    prompt: Optional[str] = None

class Report(BaseModel):
    report_type: str
    start_date: datetime
    end_date: datetime
    data: Dict[str, Any]
    generated_at: datetime = Field(default_factory=datetime.now)

class AIReport(Report):
    summary: str
    recommendations: Optional[List[str]] = None

class PurchaseOrder(BaseModel):
    branch_id: str
    product_type: str
    quantity: float
    unit_price: float
    total_amount: float
    requested_by: str
    status: str = "pending"  # pending, approved, rejected, completed
    payment_status: str = "pending"  # pending, partial, completed
    payment_amount: Optional[float] = 0
    payment_reference: Optional[str] = None
    supplier: Optional[str] = None
    expected_delivery_date: Optional[datetime] = None
    notes: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class PurchaseOrderInDB(PurchaseOrder):
    id: int
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    
class DailyChecklist(BaseModel):
    branch_id: str
    completed_by: str
    date: datetime = Field(default_factory=datetime.now)
    dispenser_test_done: bool = False
    pump_cleaning_done: bool = False
    bathroom_cleaning_done: bool = False
    notes: Optional[str] = None
    
class DailyChecklistInDB(DailyChecklist):
    id: int
    
class TotalizerReading(BaseModel):
    pump_id: str
    nozzle_id: str
    product_type: str
    reading_type: str  # 'opening' or 'closing'
    reading_value: float
    totalizer_image_url: Optional[str] = None
    pumpman_id: str
    shift: str
    branch_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
class TotalizerReadingInDB(TotalizerReading):
    id: int
    
class ShiftSales(BaseModel):
    pump_id: str
    nozzle_id: str
    product_type: str
    opening_reading: float
    closing_reading: float
    pumpman_id: str
    shift: str
    branch_id: str
    amount: float
    units_sold: float
    date: datetime = Field(default_factory=datetime.now)
    
class ShiftSalesInDB(ShiftSales):
    id: int
    
class CreditCustomer(BaseModel):
    name: str
    customer_id: str
    customer_type: str  # 'general' or 'government'
    contact_person: Optional[str] = None
    phone_number: str
    whatsapp_number: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    credit_limit: float = 0
    current_balance: float = 0
    last_payment_date: Optional[datetime] = None
    branch_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    status: str = "active"  # active, inactive, blacklisted
    credit_days: int = 30  # Default credit period in days
    
class CreditCustomerInDB(CreditCustomer):
    id: int
    
class CreditTransaction(BaseModel):
    customer_id: str
    transaction_type: str  # 'purchase', 'payment'
    amount: float
    sale_id: Optional[int] = None
    reference_number: Optional[str] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None
    branch_id: str
    recorded_by: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
class CreditTransactionInDB(CreditTransaction):
    id: int
    balance_after: float

# Product Management Models
class ProductCategory(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    branch_id: str
    
class ProductCategoryInDB(ProductCategory):
    id: str

class Product(BaseModel):
    id: str
    name: str
    category_id: str
    description: Optional[str] = None
    unit_price: float
    cost_price: Optional[float] = None
    stock_quantity: float = 0
    minimum_stock_level: Optional[float] = None
    unit_of_measure: str  # e.g., "liters", "pieces", "bottles"
    is_fuel: bool = False
    is_active: bool = True
    barcode: Optional[str] = None
    image_url: Optional[str] = None
    branch_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

class ProductInDB(Product):
    id: str
    
# Authentication Models
class UserRole(str, enum.Enum):
    ADMIN = "admin"  # Full overview access
    SENIOR_MANAGER = "branch_manager"  # Branch level access
    PUMPMAN = "pumpman"  # Limited individual access
    
class User(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.PUMPMAN  # Default to PUMPMAN role since MANAGER doesn't exist
    branch_id: Optional[str] = None
    tenant_id: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: Optional[int] = None  # User ID who created this user
    
class UserCreate(User):
    password: str
    
class UserInDB(User):
    id: int
    password_hash: str
    
class UserLogin(BaseModel):
    username: str
    password: str
    remember_me: bool = False