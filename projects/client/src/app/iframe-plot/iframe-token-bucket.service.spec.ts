import { TestBed } from '@angular/core/testing';

import { IframeTokenBucketService } from './iframe-token-bucket.service';

describe('IframeTokenBucketService', () => {
  let service: IframeTokenBucketService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(IframeTokenBucketService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
