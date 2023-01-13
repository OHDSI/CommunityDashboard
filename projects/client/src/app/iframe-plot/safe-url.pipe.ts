import { Pipe, PipeTransform, SecurityContext } from '@angular/core';
import { DomSanitizer } from '@angular/platform-browser';

@Pipe({
  name: 'safeUrl',
  standalone: true
})
export class SafeUrlPipe implements PipeTransform {

  constructor(private domSanitizer: DomSanitizer) {}
  
  transform(url: string) {
    const sanitized = this.domSanitizer.sanitize(SecurityContext.URL, url)
    if (sanitized) {
      return this.domSanitizer.bypassSecurityTrustResourceUrl(sanitized)
    } else {
      throw Error(`unsafe url: ${url}`)
    }
  }

}
