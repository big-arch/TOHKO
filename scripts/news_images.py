"""Bounded publisher-image input for the existing news request, not a second API call."""
import base64
import io
from urllib.parse import urlsplit,urljoin
from urllib.request import Request,HTTPRedirectHandler,build_opener
from news_feed import IMAGE_HOSTS

def allowed_image(url,source):
    try:
        p=urlsplit(url);host=(p.hostname or '').removeprefix('www.')
        allowed={(urlsplit(source['site']).hostname or '').removeprefix('www.')}|IMAGE_HOSTS.get(source['id'],set())
        return p.scheme=='https' and not p.username and not p.password and p.port in (None,443) and host in allowed
    except (ValueError,KeyError,TypeError):return False

class ImageRedirect(HTTPRedirectHandler):
    max_redirections=2
    def __init__(self,source):self.source=source
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        target=urljoin(req.full_url,newurl)
        if not allowed_image(target,self.source):raise ValueError('Image leaves publisher hosts')
        return super().redirect_request(req,fp,code,msg,headers,target)

def image_input(photo,source):
    """A failed photo never blocks readable article text. No remote URL reaches the model."""
    try:
        if not allowed_image(photo.get('src',''),source):return None
        from PIL import Image,ImageOps
        with build_opener(ImageRedirect(source)).open(Request(photo['src'],headers={'User-Agent':'TONKO-News/1.0'}),timeout=15) as response:
            if not response.headers.get('Content-Type','').startswith('image/'):return None
            raw=response.read(6_000_001)
        if len(raw)>6_000_000:return None
        im=Image.open(io.BytesIO(raw))
        if im.width*im.height>24_000_000 or min(im.size)<200:return None
        im=ImageOps.exif_transpose(im).convert('RGB');im.thumbnail((1024,1024))
        buf=io.BytesIO();im.save(buf,'JPEG',quality=80)
        return 'data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode('ascii')
    except Exception:return None

def reviewed_photo(item,answer):
    candidate=item.get('_coverCandidate')
    if not candidate or not item.get('_imageInput') or answer.get('photoSuitable') is not True:return None
    alt=answer.get('photoAlt')
    if not isinstance(alt,str) or not 10<=len(alt)<=500 or any(t in alt for t in ('<','>','http:','https:')):return None
    return {**candidate,'alt':alt,'caption':'Фотография этой публикации у издателя. Соответствие теме проверено автоматически.'}
