from .enquiry import Enquiry, ErpEnquiry
from .recruitment import (
    Designation,
    JobPosting,
    JobResponsibility,
    JobRequirement,
    JobPostingSkill,
    JobWhyJoinUs,
    JobApplication,
)
from .offer_letter import (
    StatusChoices,
    DutyTypeChoices,
    OfferLetter,
    OfferLetterSection,
    OfferLetterSubtitle,
    OfferLetterPoint,
    OfferLetterAnnexure,
)
from .hr_policy import HRPolicy, HRPolicySection, HRPolicySubtitle, HRPolicyPoint

__all__ = [
    'Enquiry',
    'ErpEnquiry',
    'Designation',
    'JobPosting',
    'JobResponsibility',
    'JobRequirement',
    'JobPostingSkill',
    'JobWhyJoinUs',
    'JobApplication',
    'StatusChoices',
    'DutyTypeChoices',
    'OfferLetter',
    'OfferLetterSection',
    'OfferLetterSubtitle',
    'OfferLetterPoint',
    'OfferLetterAnnexure',
    'HRPolicy',
    'HRPolicySection',
    'HRPolicySubtitle',
    'HRPolicyPoint',
]

