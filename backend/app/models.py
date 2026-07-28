import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from .database import Base


class ComplaintRecord(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    complaint_number = Column(String(50), unique=True, index=True, nullable=False)
    customer_name = Column(String(255), default="")
    complaint_source = Column(String(255), default="")
    product_name = Column(String(255), default="")
    strength_grade = Column(String(100), default="")
    batch_lot_number = Column(String(100), default="")
    manufacturing_date = Column(String(100), default="")
    expiry_date = Column(String(100), default="")
    affected_quantity = Column(String(100), default="")
    originating_site = Column(String(255), default="")
    impacted_material = Column(String(255), default="")
    complaint_type = Column(String(100), default="")
    complaint_date = Column(String(100), default="")
    defect_summary = Column(Text, default="")
    detailed_description = Column(Text, default="")
    severity = Column(String(50), default="")
    priority = Column(String(50), default="")
    risk_assessment = Column(Text, default="")
    status = Column(String(50), default="Committed")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "complaintNumber": self.complaint_number,
            "customerName": self.customer_name,
            "complaintSource": self.complaint_source,
            "productName": self.product_name,
            "strengthGrade": self.strength_grade,
            "batchLotNumber": self.batch_lot_number,
            "manufacturingDate": self.manufacturing_date,
            "expiryDate": self.expiry_date,
            "affectedQuantity": self.affected_quantity,
            "originatingSite": self.originating_site,
            "impactedMaterial": self.impacted_material,
            "complaintType": self.complaint_type,
            "complaintDate": self.complaint_date,
            "defectSummary": self.defect_summary,
            "detailedDescription": self.detailed_description,
            "severity": self.severity,
            "priority": self.priority,
            "riskAssessment": self.risk_assessment,
            "status": self.status,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
