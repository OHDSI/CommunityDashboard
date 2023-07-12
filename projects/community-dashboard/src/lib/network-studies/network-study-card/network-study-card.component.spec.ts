import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NetworkStudyCardComponent } from './network-study-card.component';

describe('NetworkStudyCardComponent', () => {
  let component: NetworkStudyCardComponent;
  let fixture: ComponentFixture<NetworkStudyCardComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [NetworkStudyCardComponent]
    });
    fixture = TestBed.createComponent(NetworkStudyCardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
