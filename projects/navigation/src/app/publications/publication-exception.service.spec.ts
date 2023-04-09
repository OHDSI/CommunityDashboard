import { TestBed } from '@angular/core/testing';
import { PublicationExceptionService } from './publication-exception.service';


describe('PublicationExceptionService', () => {
  let service: PublicationExceptionService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(PublicationExceptionService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
