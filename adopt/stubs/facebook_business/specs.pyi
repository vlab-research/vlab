from facebook_business.adobjects import adcreativelinkdata as adcreativelinkdata, adcreativelinkdatachildattachment as adcreativelinkdatachildattachment, adcreativeobjectstoryspec as adcreativeobjectstoryspec, adcreativephotodata as adcreativephotodata, adcreativetextdata as adcreativetextdata, adcreativevideodata as adcreativevideodata, pagepost as pagepost, user as user
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.mixins import ValidatesFields as ValidatesFields

class ObjectStorySpec(adcreativeobjectstoryspec.AdCreativeObjectStorySpec): ...
class AttachmentData(adcreativelinkdatachildattachment.AdCreativeLinkDataChildAttachment): ...
class LinkData(adcreativelinkdata.AdCreativeLinkData): ...
class TemplateData(adcreativelinkdata.AdCreativeLinkData): ...
class TextData(adcreativetextdata.AdCreativeTextData): ...
class PhotoData(adcreativephotodata.AdCreativePhotoData): ...
class VideoData(adcreativevideodata.AdCreativeVideoData): ...
class PagePostData(pagepost.PagePost): ...
class UserData(user.User): ...

class SlideshowSpec(ValidatesFields, AbstractObject):
    class Field:
        images_urls: str
        duration_ms: str
        transition_ms: str
