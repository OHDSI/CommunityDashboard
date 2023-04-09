import { TestBed } from '@angular/core/testing';
import { PublicationsManualService } from './publications-manual.service';


describe('PublicationsManualService', () => {
  let service: PublicationsManualService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(PublicationsManualService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
