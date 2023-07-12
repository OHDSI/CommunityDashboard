import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NetworkStudyListComponent } from './network-study-list.component';

describe('NetworkStudyListComponent', () => {
  let component: NetworkStudyListComponent;
  let fixture: ComponentFixture<NetworkStudyListComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [NetworkStudyListComponent]
    });
    fixture = TestBed.createComponent(NetworkStudyListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
