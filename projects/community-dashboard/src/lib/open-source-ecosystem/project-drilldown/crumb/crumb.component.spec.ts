import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CrumbComponent } from './crumb.component';

describe('CrumbComponent', () => {
  let component: CrumbComponent;
  let fixture: ComponentFixture<CrumbComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [CrumbComponent]
    });
    fixture = TestBed.createComponent(CrumbComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
