import { TestBed } from '@angular/core/testing';

import { EhdenService } from './ehden.service';

describe('EhdenService', () => {
  let service: EhdenService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(EhdenService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
