import { TestBed } from '@angular/core/testing';
import { DomSanitizer } from '@angular/platform-browser';
import { SafeUrlPipe } from './safe-url.pipe';

describe('SafeUrlPipe', () => {

  beforeEach(async () => {
    TestBed.configureTestingModule({
      providers: [ DomSanitizer ]
    })
  });

  it('create an instance', () => {
    const pipe = new SafeUrlPipe(TestBed.inject(DomSanitizer));
    expect(pipe).toBeTruthy();
  });
});
